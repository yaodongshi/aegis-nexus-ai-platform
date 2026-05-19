from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from pydantic import ValidationError

from ..schemas import (
    ActionChainTemplateCreateRequest,
    ActionChainTemplateRecord,
    ActionChainTemplateRunRequest,
    ActionChainTemplateRunResponse,
    AgentWorkflowRecord,
    EvolutionActionLogRecord,
    EvolutionOverviewResponse,
    GatewayKnowledgeIngestRequest,
    GatewayKnowledgeIngestResponse,
    GenerateAgentWorkflowRequest,
    GenerateAgentWorkflowResponse,
    GitRepoCreateRequest,
    GitRepoPullSyncResponse,
    GitRepoProbeResponse,
    GitRepoRecord,
    GitRepoUpdateRequest,
    OptimizeAgentWorkflowRequest,
    OptimizeAgentWorkflowResponse,
    PassiveRagIngestRequest,
    PassiveRagIngestResponse,
    ReplayEvolutionActionChainRequest,
    ReplayEvolutionActionChainResponse,
    HookSecretRotateRequest,
    HookSecretRotateResponse,
    HookSecretStatusResponse,
    PageResponse,
    RagSummarizeToSkillRequest,
    RagSummarizeToSkillResponse,
    SkillBundleRecord,
    SkillBundleUploadRequest,
    SkillBundleUploadResponse,
    SkillHookEventRecord,
    SkillUpdateRecord,
    SkillUpdateSyncRequest,
    SkillHookReportRequest,
    SkillHookReportResponse,
    TaskRunRecord,
    TaskRunReportRequest,
    TaskRunReportResponse,
    TeamSkillSyncApplyRequest,
    TeamSkillSyncApplyResponse,
    TeamSkillSyncRuleResponse,
)
from ..store import PlatformStore
from .dependencies import get_store, require_admin_token

router = APIRouter(prefix="/api", tags=["learning"])


def _compute_hook_signature(secret: str, payload: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _build_hook_idempotency_key(payload: SkillHookReportRequest) -> str:
    canonical = {
        "repository": payload.repository,
        "repo_id": payload.repo_id,
        "branch": payload.branch,
        "commit_sha": payload.commit_sha,
        "changed_files": sorted(str(item).strip() for item in payload.changed_files if str(item).strip()),
    }
    raw = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def require_agent_token(
    x_agent_token: str | None = Header(default=None, alias="X-Agent-Token"),
    authorization: str | None = Header(default=None),
) -> None:
    expected_token = os.getenv("TEAM_AI_PLATFORM_AGENT_TOKEN", "").strip()
    if not expected_token:
        return

    bearer_token = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()
    provided_token = (x_agent_token or bearer_token or "").strip()

    if not provided_token or not secrets.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent token")


@router.post("/task-runs/report", response_model=TaskRunReportResponse, status_code=status.HTTP_201_CREATED)
def report_task_run(
    payload: TaskRunReportRequest,
    store: PlatformStore = Depends(get_store),
    _: None = Depends(require_agent_token),
) -> TaskRunReportResponse:
    return store.report_task_run(payload)


@router.post("/skill-sync/hooks/report", response_model=SkillHookReportResponse, status_code=status.HTTP_201_CREATED)
async def report_skill_hook(
    request: Request,
    store: PlatformStore = Depends(get_store),
    x_hook_signature: str | None = Header(default=None, alias="X-Hook-Signature"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> SkillHookReportResponse:
    raw_body = await request.body()
    try:
        payload = SkillHookReportRequest.model_validate_json(raw_body)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()) from exc

    hook_secret = store.get_effective_hook_secret()
    if hook_secret:
        if not x_hook_signature:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing hook signature")
        expected_signature = _compute_hook_signature(hook_secret, raw_body)
        if not secrets.compare_digest(x_hook_signature.strip(), expected_signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid hook signature")

    idempotency_key = (x_idempotency_key or "").strip() or _build_hook_idempotency_key(payload)
    result = store.report_skill_hook_event(payload, idempotency_key=idempotency_key)
    if not result.created:
        return result
    return result


@router.post(
    "/skill-sync/rag/ingest",
    response_model=PassiveRagIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_passive_rag(
    payload: PassiveRagIngestRequest,
    store: PlatformStore = Depends(get_store),
    _: None = Depends(require_agent_token),
) -> PassiveRagIngestResponse:
    return store.ingest_passive_rag_items(payload)


@router.post(
    "/skill-sync/mcp/skill-bundles/upload",
    response_model=SkillBundleUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_skill_bundle_via_mcp(
    payload: SkillBundleUploadRequest,
    store: PlatformStore = Depends(get_store),
    _: None = Depends(require_agent_token),
) -> SkillBundleUploadResponse:
    return store.upload_skill_bundle(payload)


@router.get(
    "/skill-sync/mcp/skill-bundles/download",
    response_model=SkillBundleRecord,
    dependencies=[Depends(require_admin_token)],
)
def download_skill_bundle_via_mcp(
    skill_id: str,
    version: str | None = Query(default=None),
    store: PlatformStore = Depends(get_store),
) -> SkillBundleRecord:
    bundle = store.download_skill_bundle(skill_id, version=version)
    if bundle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill bundle not found")
    return bundle


@router.post(
    "/skill-sync/mcp/team-rules/generate",
    response_model=TeamSkillSyncRuleResponse,
    dependencies=[Depends(require_admin_token)],
)
def generate_team_skill_sync_rules(
    team_id: str,
    store: PlatformStore = Depends(get_store),
) -> TeamSkillSyncRuleResponse:
    return store.generate_team_skill_sync_rules(team_id)


@router.post(
    "/skill-sync/mcp/team-rules/{rule_set_id}/apply",
    response_model=TeamSkillSyncApplyResponse,
    dependencies=[Depends(require_admin_token)],
)
def apply_team_skill_sync_rules(
    team_id: str,
    rule_set_id: str,
    payload: TeamSkillSyncApplyRequest,
    store: PlatformStore = Depends(get_store),
) -> TeamSkillSyncApplyResponse:
    try:
        return store.sync_team_skills(team_id, rule_set_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/evolution/gateway-knowledge/ingest",
    response_model=GatewayKnowledgeIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_gateway_knowledge(
    payload: GatewayKnowledgeIngestRequest,
    store: PlatformStore = Depends(get_store),
    _: None = Depends(require_agent_token),
) -> GatewayKnowledgeIngestResponse:
    return store.ingest_gateway_knowledge(payload)


@router.post(
    "/evolution/rag-to-skill/summarize",
    response_model=RagSummarizeToSkillResponse,
    dependencies=[Depends(require_admin_token)],
)
def summarize_rag_to_skill(
    payload: RagSummarizeToSkillRequest,
    store: PlatformStore = Depends(get_store),
) -> RagSummarizeToSkillResponse:
    return store.summarize_rag_to_skill(payload)


@router.post(
    "/evolution/rag-to-agent/generate",
    response_model=GenerateAgentWorkflowResponse,
    dependencies=[Depends(require_admin_token)],
)
def generate_agent_workflow(
    payload: GenerateAgentWorkflowRequest,
    store: PlatformStore = Depends(get_store),
) -> GenerateAgentWorkflowResponse:
    return store.generate_agent_workflow_from_rag(payload)


@router.post(
    "/evolution/rag-to-agent/{workflow_id}/optimize",
    response_model=OptimizeAgentWorkflowResponse,
    dependencies=[Depends(require_admin_token)],
)
def optimize_agent_workflow(
    workflow_id: str,
    payload: OptimizeAgentWorkflowRequest,
    store: PlatformStore = Depends(get_store),
) -> OptimizeAgentWorkflowResponse:
    optimized = store.optimize_agent_workflow(workflow_id, payload)
    if optimized is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent workflow not found")
    return optimized


@router.get(
    "/evolution/rag-to-agent/workflows",
    response_model=PageResponse[AgentWorkflowRecord],
    dependencies=[Depends(require_admin_token)],
)
def list_agent_workflows(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[AgentWorkflowRecord]:
    records = sorted(
        store.agent_workflows.values(),
        key=lambda item: item.updated_at,
        reverse=True,
    )
    paged = records[offset : offset + limit]
    return PageResponse[AgentWorkflowRecord](
        items=paged,
        total=len(records),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/evolution/overview",
    response_model=EvolutionOverviewResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_evolution_overview(
    store: PlatformStore = Depends(get_store),
) -> EvolutionOverviewResponse:
    return store.get_evolution_overview()


@router.get(
    "/evolution/actions",
    response_model=PageResponse[EvolutionActionLogRecord],
    dependencies=[Depends(require_admin_token)],
)
def list_evolution_actions(
    action_name: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    window_minutes: int | None = Query(default=None, ge=1, le=1440),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[EvolutionActionLogRecord]:
    since = None
    if window_minutes is not None:
        since = datetime.now(UTC) - timedelta(minutes=window_minutes)

    records = store.list_evolution_action_logs(
        action_name=action_name,
        status=status_filter,
        since=since,
        limit=limit,
        offset=offset,
    )
    return PageResponse[EvolutionActionLogRecord](
        items=records,
        total=len(records),
        limit=limit,
        offset=offset,
    )


@router.post(
    "/evolution/action-templates",
    response_model=ActionChainTemplateRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_token)],
)
def create_action_chain_template(
    payload: ActionChainTemplateCreateRequest,
    store: PlatformStore = Depends(get_store),
) -> ActionChainTemplateRecord:
    return store.create_action_chain_template(payload)


@router.get(
    "/evolution/action-templates",
    response_model=PageResponse[ActionChainTemplateRecord],
    dependencies=[Depends(require_admin_token)],
)
def list_action_chain_templates(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[ActionChainTemplateRecord]:
    records = store.list_action_chain_templates()
    paged = records[offset : offset + limit]
    return PageResponse[ActionChainTemplateRecord](
        items=paged,
        total=len(records),
        limit=limit,
        offset=offset,
    )


@router.post(
    "/evolution/action-templates/{template_id}/run",
    response_model=ActionChainTemplateRunResponse,
    dependencies=[Depends(require_admin_token)],
)
def run_action_chain_template(
    template_id: str,
    payload: ActionChainTemplateRunRequest,
    store: PlatformStore = Depends(get_store),
) -> ActionChainTemplateRunResponse:
    result = store.run_action_chain_template(template_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action chain template not found")
    return result


@router.post(
    "/evolution/actions/replay-last-success-chain",
    response_model=ReplayEvolutionActionChainResponse,
    dependencies=[Depends(require_admin_token)],
)
def replay_last_success_action_chain(
    payload: ReplayEvolutionActionChainRequest,
    store: PlatformStore = Depends(get_store),
) -> ReplayEvolutionActionChainResponse:
    return store.replay_last_success_action_chain(payload)


@router.get(
    "/skill-sync/hooks/events",
    response_model=PageResponse[SkillHookEventRecord],
    dependencies=[Depends(require_admin_token)],
)
def list_skill_hook_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[SkillHookEventRecord]:
    items = store.list_skill_hook_events(limit=limit, offset=offset)
    return PageResponse[SkillHookEventRecord](items=items, total=len(items), limit=limit, offset=offset)


@router.get(
    "/skill-sync/hooks/secret",
    response_model=HookSecretStatusResponse,
    dependencies=[Depends(require_admin_token)],
)
def get_hook_secret_status(store: PlatformStore = Depends(get_store)) -> HookSecretStatusResponse:
    return store.get_hook_secret_status()


@router.post(
    "/skill-sync/hooks/secret/rotate",
    response_model=HookSecretRotateResponse,
    dependencies=[Depends(require_admin_token)],
)
def rotate_hook_secret(
    payload: HookSecretRotateRequest,
    store: PlatformStore = Depends(get_store),
) -> HookSecretRotateResponse:
    return store.rotate_hook_secret(payload.new_secret)


@router.get(
    "/task-runs",
    response_model=PageResponse[TaskRunRecord],
    dependencies=[Depends(require_admin_token)],
)
def list_task_runs(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[TaskRunRecord]:
    records = store.list_task_runs()
    paged = records[offset : offset + limit]
    return PageResponse[TaskRunRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.get(
    "/skill-updates",
    response_model=PageResponse[SkillUpdateRecord],
    dependencies=[Depends(require_admin_token)],
)
def list_skill_updates(
    status_filter: str | None = Query(default=None, alias="status"),
    skill_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[SkillUpdateRecord]:
    records = store.list_skill_updates(status=status_filter, skill_id=skill_id)
    paged = records[offset : offset + limit]
    return PageResponse[SkillUpdateRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.post(
    "/skill-updates/{update_id}/apply",
    response_model=SkillUpdateRecord,
    dependencies=[Depends(require_admin_token)],
)
def apply_skill_update(update_id: str, store: PlatformStore = Depends(get_store)) -> SkillUpdateRecord:
    updated = store.apply_skill_update(update_id)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill update not found")
    return updated


@router.post(
    "/skill-updates/{update_id}/sync",
    response_model=SkillUpdateRecord,
    dependencies=[Depends(require_admin_token)],
)
def sync_skill_update(
    update_id: str,
    payload: SkillUpdateSyncRequest,
    store: PlatformStore = Depends(get_store),
) -> SkillUpdateRecord:
    try:
        updated = store.sync_skill_update(update_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill update not found")
    return updated


@router.get(
    "/git-repos",
    response_model=PageResponse[GitRepoRecord],
    dependencies=[Depends(require_admin_token)],
)
def list_git_repos(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[GitRepoRecord]:
    records = store.list_git_repos()
    paged = records[offset : offset + limit]
    return PageResponse[GitRepoRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.get(
    "/git-repos/active",
    response_model=GitRepoRecord,
    dependencies=[Depends(require_admin_token)],
)
def get_active_git_repo(store: PlatformStore = Depends(get_store)) -> GitRepoRecord:
    active = store.get_active_git_repo()
    if active is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active git repository not configured")
    return active


@router.post(
    "/git-repos",
    response_model=GitRepoRecord,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_token)],
)
def create_git_repo(
    payload: GitRepoCreateRequest,
    store: PlatformStore = Depends(get_store),
) -> GitRepoRecord:
    try:
        return store.create_git_repo(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch(
    "/git-repos/{repo_id}",
    response_model=GitRepoRecord,
    dependencies=[Depends(require_admin_token)],
)
def update_git_repo(
    repo_id: str,
    payload: GitRepoUpdateRequest,
    store: PlatformStore = Depends(get_store),
) -> GitRepoRecord:
    try:
        updated = store.update_git_repo(repo_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Git repository not found")
    return updated


@router.post(
    "/git-repos/{repo_id}/activate",
    response_model=GitRepoRecord,
    dependencies=[Depends(require_admin_token)],
)
def activate_git_repo(repo_id: str, store: PlatformStore = Depends(get_store)) -> GitRepoRecord:
    active = store.activate_git_repo(repo_id)
    if active is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Git repository not found")
    return active


@router.get(
    "/git-repos/{repo_id}/probe",
    response_model=GitRepoProbeResponse,
    dependencies=[Depends(require_admin_token)],
)
def probe_git_repo(repo_id: str, store: PlatformStore = Depends(get_store)) -> GitRepoProbeResponse:
    probe = store.probe_git_repo(repo_id)
    if probe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Git repository not found")
    return probe


@router.post(
    "/git-repos/{repo_id}/pull",
    response_model=GitRepoPullSyncResponse,
    dependencies=[Depends(require_admin_token)],
)
def pull_git_repo_skills(repo_id: str, store: PlatformStore = Depends(get_store)) -> GitRepoPullSyncResponse:
    try:
        result = store.pull_git_repo_skills(repo_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Git repository not found")
    return result


@router.delete(
    "/git-repos/{repo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin_token)],
)
def delete_git_repo(repo_id: str, store: PlatformStore = Depends(get_store)) -> Response:
    deleted = store.delete_git_repo(repo_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Git repository not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
