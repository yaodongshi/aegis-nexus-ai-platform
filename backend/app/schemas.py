from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0


class ModelRecord(BaseModel):
    id: str
    provider: str
    provider_id: str | None = None
    upstream_model: str | None = None
    name: str
    endpoint: str
    context_window: int
    cost_tier: str
    availability: str = "active"
    deployment_status: str = "active"
    tags: list[str] = Field(default_factory=list)
    labels: dict[str, Any] = Field(default_factory=dict)
    quota: int | None = None
    created_at: datetime
    updated_at: datetime


class ModelRegisterRequest(BaseModel):
    provider: str
    provider_id: str | None = None
    upstream_model: str | None = None
    name: str
    endpoint: str
    context_window: int
    cost_tier: str
    deployment_status: str = "active"
    tags: list[str] = Field(default_factory=list)
    labels: dict[str, Any] = Field(default_factory=dict)
    quota: int | None = None


class ModelBatchRegisterRequest(BaseModel):
    models: list[ModelRegisterRequest] = Field(default_factory=list)


class ModelBatchRegisterResponse(BaseModel):
    total: int = 0
    registered: int = 0
    skipped: int = 0
    items: list[ModelRecord] = Field(default_factory=list)


class ModelUpdateRequest(BaseModel):
    provider_id: str | None = None
    upstream_model: str | None = None
    endpoint: str | None = None
    context_window: int | None = None
    cost_tier: str | None = None
    availability: str | None = None
    deployment_status: str | None = None
    tags: list[str] | None = None
    labels: dict[str, Any] | None = None
    quota: int | None = None


class ModelBatchDeleteRequest(BaseModel):
    model_ids: list[str] = Field(default_factory=list)


class ModelBatchDeleteResponse(BaseModel):
    total: int = 0
    deleted: int = 0
    deleted_ids: list[str] = Field(default_factory=list)
    missing_ids: list[str] = Field(default_factory=list)


class KeyIssueRequest(BaseModel):
    label: str | None = None
    user_id: str = "admin"
    project_id: str | None = None
    scope: str = "project:*"
    expire_at: datetime | None = None
    expires_days: int | None = None
    quota: int | None = None


class KeyRecord(BaseModel):
    id: str
    key_hash: str
    label: str | None = None
    user_id: str | None = None
    project_id: str | None = None
    scope: str
    expire_at: datetime | None = None
    quota: int | None = None
    status: Literal["active", "revoked"] = "active"
    litellm_key_id: str | None = None  # LiteLLM 分配的 key 标识，用于撤销
    created_at: datetime
    updated_at: datetime


class KeyIssueResponse(BaseModel):
    key_id: str
    key_secret: str
    label: str | None = None
    user_id: str | None = None
    project_id: str | None = None
    status: str
    expire_at: datetime | None = None


class SkillCreateRequest(BaseModel):
    name: str
    description: str = ""
    system_prompt: str = ""
    category: str = "general"
    tags: list[str] = Field(default_factory=list)


class SkillUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class SkillRecord(BaseModel):
    id: str
    name: str
    description: str = ""
    system_prompt: str = ""
    category: str = "general"
    tags: list[str] = Field(default_factory=list)
    status: str = "active"
    created_at: datetime
    updated_at: datetime


class SkillSearchStatusResponse(BaseModel):
    mode: Literal["vector", "lexical", "warming"] = "lexical"
    qdrant_enabled: bool = False
    qdrant_url: str
    qdrant_collection: str
    embedding_model: str
    embedding_available: bool = False
    last_search_mode: Literal["vector", "lexical"] | None = None
    last_search_latency_ms: int | None = None
    last_search_result_count: int | None = None
    last_error: str | None = None
    next_retry_at: datetime | None = None


class SkillPackFile(BaseModel):
    path: str
    description: str = ""
    content: str


class SkillPackExportResponse(BaseModel):
    protocol_version: str = "1.0"
    target: str
    skill_id: str
    skill_name: str
    generated_at: datetime
    install_hint: str
    files: list[SkillPackFile] = Field(default_factory=list)


class SessionRecord(BaseModel):
    id: str
    user_id: str
    project_id: str | None = None
    title: str | None = None
    summary: str | None = None
    memory_vector_id: str | None = None
    status: str = "active"
    created_at: datetime
    updated_at: datetime


class SessionCreateRequest(BaseModel):
    user_id: str
    project_id: str | None = None
    title: str | None = None
    summary: str | None = None


class SessionUpdateRequest(BaseModel):
    title: str | None = None
    summary: str | None = None
    status: str | None = None
    memory_vector_id: str | None = None


class PolicyRecord(BaseModel):
    id: str
    name: str
    type: str
    rules: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"
    created_at: datetime
    updated_at: datetime


class PolicyUpsertRequest(BaseModel):
    name: str
    type: str
    rules: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"


class ApprovalRecord(BaseModel):
    id: str
    applicant_id: str
    action: str
    resource_id: str
    status: Literal["pending", "approved", "rejected", "canceled"] = "pending"
    approver_id: str | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ApprovalSubmitRequest(BaseModel):
    applicant_id: str
    action: str
    resource_id: str
    reason: str


class ProviderPresetRecord(BaseModel):
    key: str
    name: str
    provider_type: str
    default_base_url: str
    api_format: Literal["openai", "anthropic", "openai_responses"] = "openai"
    suggested_apps: list[str] = Field(default_factory=list)


class ProviderModelMappingRecord(BaseModel):
    alias: str
    upstream_model: str
    note: str | None = None


class ProviderCreateRequest(BaseModel):
    name: str
    provider_type: str
    base_url: str
    api_key: str
    preset_key: str | None = None
    scope: Literal["app", "unified"] = "app"
    apps: list[str] = Field(default_factory=list)
    api_format: Literal["openai", "anthropic", "openai_responses"] = "openai"
    notes: str | None = None
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    model_mappings: list[ProviderModelMappingRecord] = Field(
        default_factory=list
    )


class ProviderUpdateRequest(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    preset_key: str | None = None
    scope: Literal["app", "unified"] | None = None
    apps: list[str] | None = None
    api_format: (
        Literal["openai", "anthropic", "openai_responses"] | None
    ) = None
    notes: str | None = None
    enabled: bool | None = None
    metadata: dict[str, Any] | None = None
    model_mappings: list[ProviderModelMappingRecord] | None = None


class ProviderRecord(BaseModel):
    id: str
    name: str
    provider_type: str
    base_url: str
    preset_key: str | None = None
    scope: Literal["app", "unified"] = "app"
    apps: list[str] = Field(default_factory=list)
    api_format: Literal["openai", "anthropic", "openai_responses"] = "openai"
    notes: str | None = None
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    model_mappings: list[ProviderModelMappingRecord] = Field(
        default_factory=list
    )
    api_key_masked: str | None = None
    created_at: datetime
    updated_at: datetime


class ProviderSyncRequest(BaseModel):
    target_apps: list[str] = Field(default_factory=list)
    sync_models: bool = True


class ProviderModelDiscoveryResponse(BaseModel):
    provider_id: str
    endpoint: str
    models: list[str] = Field(default_factory=list)
    fetched_at: datetime


class ProviderLiveModelDiscoveryRequest(BaseModel):
    provider_type: str
    base_url: str
    api_key: str


class ProviderLiveModelDiscoveryResponse(BaseModel):
    endpoint: str
    models: list[str] = Field(default_factory=list)
    fetched_at: datetime


class ProviderGatewaySyncResponse(BaseModel):
    ok: bool = False
    model_count: int = 0
    endpoint: str | None = None
    detail: str | None = None
    synced_at: datetime


class ProviderProbeRequest(BaseModel):
    endpoints: list[str] = Field(default_factory=list)
    timeout_ms: int = 5000


class ProviderProbeResult(BaseModel):
    endpoint: str
    ok: bool
    status_code: int | None = None
    latency_ms: int | None = None
    error: str | None = None


class ProviderProbeResponse(BaseModel):
    provider_id: str
    best_endpoint: str | None = None
    results: list[ProviderProbeResult] = Field(default_factory=list)
    probed_at: datetime


class ProviderProbeLogRecord(BaseModel):
    id: str
    provider_id: str
    best_endpoint: str | None = None
    results: list[ProviderProbeResult] = Field(default_factory=list)
    probed_at: datetime


class ProviderBatchProbeRequest(BaseModel):
    provider_ids: list[str] = Field(default_factory=list)
    timeout_ms: int = 5000
    apply_best_endpoint: bool = False


class ProviderBatchProbeItem(BaseModel):
    provider_id: str
    provider_name: str
    best_endpoint: str | None = None
    applied: bool = False
    results: list[ProviderProbeResult] = Field(default_factory=list)


class ProviderBatchProbeResponse(BaseModel):
    items: list[ProviderBatchProbeItem] = Field(default_factory=list)
    total: int = 0
    succeeded: int = 0
    probed_at: datetime


class ProviderBatchUpdateRequest(BaseModel):
    provider_ids: list[str] = Field(default_factory=list)
    enabled: bool | None = None
    target_apps: list[str] | None = None
    force_unified: bool = False


class ProviderBatchUpdateResponse(BaseModel):
    total: int = 0
    updated: int = 0
    updated_ids: list[str] = Field(default_factory=list)
    skipped_ids: list[str] = Field(default_factory=list)


class ProviderBatchDeleteRequest(BaseModel):
    provider_ids: list[str] = Field(default_factory=list)


class ProviderBatchDeleteResponse(BaseModel):
    total: int = 0
    deleted: int = 0
    deleted_ids: list[str] = Field(default_factory=list)
    skipped_ids: list[str] = Field(default_factory=list)


class RuntimeConfigApplyRequest(BaseModel):
    output_dir: str | None = None


class RuntimeConfigPreviewResponse(BaseModel):
    provider_count: int = 0
    model_count: int = 0
    observability_backend: str = "none"
    config: dict[str, Any] = Field(default_factory=dict)


class RuntimeConfigApplyResponse(BaseModel):
    provider_count: int = 0
    model_count: int = 0
    observability_backend: str = "none"
    config_path: str
    env_path: str
    written_at: datetime


class ClientRuntimeConfigResponse(BaseModel):
    app: str
    gateway_base_url: str
    model_count: int = 0
    models: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime


class PlatformServiceStatus(BaseModel):
    name: str
    url: str
    reachable: bool


class V2VirtualKeyCreateRequest(BaseModel):
    team_id: str
    alias: str | None = None
    owner_type: Literal["user", "project", "service"] = "user"
    owner_id: str
    expires_at: datetime | None = None
    quota_tokens: int | None = None
    rate_limit_rpm: int | None = None


class V2VirtualKeyRecord(BaseModel):
    key_id: str
    team_id: str
    alias: str | None = None
    owner_type: str
    owner_id: str
    status: Literal["active", "revoked"] = "active"
    expires_at: datetime | None = None
    rotated_from: str | None = None
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None = None


class V2VirtualKeyCreateResponse(BaseModel):
    key: V2VirtualKeyRecord
    key_secret: str


class V2VirtualKeyRotateResponse(BaseModel):
    old_key_id: str
    new_key: V2VirtualKeyRecord
    new_key_secret: str


class V2OwnershipViewItem(BaseModel):
    team_id: str
    owner_type: str
    owner_id: str
    total_keys: int = 0
    active_keys: int = 0
    revoked_keys: int = 0
    last_updated_at: datetime | None = None


class V2KeyPolicyUpsertRequest(BaseModel):
    allowed_models: list[str] = Field(default_factory=list)
    denied_models: list[str] = Field(default_factory=list)
    quota_tokens_day: int | None = None
    quota_tokens_month: int | None = None
    rate_limit_rpm: int | None = None
    burst_limit: int | None = None
    emergency_block: bool = False


class V2KeyPolicyRecord(BaseModel):
    policy_id: str
    key_id: str
    allowed_models: list[str] = Field(default_factory=list)
    denied_models: list[str] = Field(default_factory=list)
    quota_tokens_day: int | None = None
    quota_tokens_month: int | None = None
    rate_limit_rpm: int | None = None
    burst_limit: int | None = None
    emergency_block: bool = False
    effective_from: datetime
    effective_to: datetime | None = None
    created_at: datetime
    updated_at: datetime
    detail: str | None = None


class PlatformOverviewResponse(BaseModel):
    providers_total: int = 0
    providers_enabled: int = 0
    keys_total: int = 0
    keys_active: int = 0
    keys_revoked: int = 0
    skills_total: int = 0
    sessions_total: int = 0
    policies_total: int = 0
    approvals_total: int = 0
    approvals_pending: int = 0
    gateway_models_total: int | None = None
    service_status: list[PlatformServiceStatus] = Field(default_factory=list)


class PlatformRuntimeHealthCheck(BaseModel):
    name: str
    ok: bool
    blocking: bool = True
    detail: str | None = None


class PlatformRuntimeHealthResponse(BaseModel):
    ok: bool = False
    litellm_base: str
    checked_at: datetime
    model_count: int = 0
    chat_model_count: int = 0
    embedding_model_count: int = 0
    checks: list[PlatformRuntimeHealthCheck] = Field(default_factory=list)


class TaskRunReportRequest(BaseModel):
    tool_type: Literal["claude_code", "codex", "other"] = "codex"
    user_id: str = "unknown"
    task_title: str
    summary: str
    error_log: str | None = None
    lessons_learned: str | None = None
    proposed_skill_name: str | None = None
    proposed_system_prompt: str | None = None
    proposed_user_prompt_template: str | None = None


class TaskRunRecord(BaseModel):
    id: str
    tool_type: Literal["claude_code", "codex", "other"] = "codex"
    user_id: str
    task_title: str
    summary: str
    error_log: str | None = None
    lessons_learned: str | None = None
    created_at: datetime
    updated_at: datetime


class SkillUpdateRecord(BaseModel):
    id: str
    task_run_id: str
    skill_id: str | None = None
    git_repo_id: str | None = None
    proposed_skill_name: str | None = None
    proposed_system_prompt: str | None = None
    proposed_user_prompt_template: str | None = None
    rationale: str
    error_patterns: str | None = None
    status: Literal["draft", "applied", "synced", "rejected"] = "draft"
    export_path: str | None = None
    git_commit_hash: str | None = None
    created_at: datetime
    updated_at: datetime


class TaskRunReportResponse(BaseModel):
    task_run: TaskRunRecord
    skill_update: SkillUpdateRecord


class SkillUpdateSyncRequest(BaseModel):
    mode: Literal["local", "git"] = "local"
    path: str | None = None
    repo_id: str | None = None
    auto_commit: bool | None = None


class GitRepoCreateRequest(BaseModel):
    name: str
    path: str
    branch: str = "main"
    auto_commit: bool = False
    make_active: bool = True


class GitRepoUpdateRequest(BaseModel):
    name: str | None = None
    path: str | None = None
    branch: str | None = None
    auto_commit: bool | None = None


class GitRepoRecord(BaseModel):
    id: str
    name: str
    path: str
    branch: str = "main"
    auto_commit: bool = False
    is_active: bool = False
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class GitRepoProbeResponse(BaseModel):
    repo_id: str
    path: str
    path_exists: bool
    is_git_repo: bool
    git_available: bool
    configured_branch: str
    active_branch: str | None = None
    configured_branch_exists: bool = False
    error: str | None = None


class SkillHookReportRequest(BaseModel):
    repository: str
    repo_id: str | None = None
    branch: str = "main"
    commit_sha: str
    changed_files: list[str] = Field(default_factory=list)
    event_id: str | None = None
    author: str | None = None
    event_time: datetime | None = None


class SkillHookReportResponse(BaseModel):
    hook_event_id: str
    idempotency_key: str
    created: bool = True
    linked_skill_ids: list[str] = Field(default_factory=list)
    detail: str | None = None


class SkillHookEventRecord(BaseModel):
    hook_event_id: str
    event_id: str | None = None
    idempotency_key: str
    repo_id: str | None = None
    repository: str
    branch: str
    commit_sha: str
    changed_files: list[str] = Field(default_factory=list)
    linked_skill_ids: list[str] = Field(default_factory=list)
    author: str | None = None
    event_time: datetime | None = None
    created_at: datetime


class PassiveRagIngestItem(BaseModel):
    source_type: Literal["commit", "pull_request", "issue", "session", "task", "custom"] = "custom"
    source_id: str
    title: str | None = None
    content: str
    repository: str | None = None
    project_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    quality_score: float = Field(default=0.7, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PassiveRagIngestRequest(BaseModel):
    items: list[PassiveRagIngestItem] = Field(min_length=1, max_length=200)
    min_quality_score: float = Field(default=0.6, ge=0.0, le=1.0)
    created_by: str | None = None


class PassiveRagIngestRejectedItem(BaseModel):
    source_id: str
    reason: str


class PassiveRagIngestResponse(BaseModel):
    received: int
    accepted: int
    rejected: int
    created_knowledge_ids: list[str] = Field(default_factory=list)
    rejected_items: list[PassiveRagIngestRejectedItem] = Field(default_factory=list)


class SkillBundleUploadRequest(BaseModel):
    team_id: str
    skill_id: str
    version: str = "v1"
    bundle: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    uploaded_by: str | None = None


class SkillBundleRecord(BaseModel):
    bundle_id: str
    team_id: str
    skill_id: str
    version: str
    tags: list[str] = Field(default_factory=list)
    uploaded_by: str | None = None
    created_at: datetime
    updated_at: datetime


class SkillBundleUploadResponse(BaseModel):
    bundle: SkillBundleRecord
    detail: str | None = None


class TeamSkillSyncRuleRecord(BaseModel):
    rule_set_id: str
    team_id: str
    based_on_bundle_ids: list[str] = Field(default_factory=list)
    synced_skill_ids: list[str] = Field(default_factory=list)
    generated_at: datetime


class TeamSkillSyncRuleResponse(BaseModel):
    rule: TeamSkillSyncRuleRecord
    detail: str | None = None


class TeamSkillSyncApplyRequest(BaseModel):
    dry_run: bool = False


class TeamSkillSyncApplyResponse(BaseModel):
    team_id: str
    rule_set_id: str
    dry_run: bool = False
    synced_skill_ids: list[str] = Field(default_factory=list)
    detail: str | None = None


class GatewayKnowledgeIngestItem(BaseModel):
    source_type: Literal["session", "cli"] = "session"
    source_id: str
    title: str | None = None
    content: str
    module: str | None = None
    team_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    quality_score: float = Field(default=0.7, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GatewayKnowledgeIngestRequest(BaseModel):
    items: list[GatewayKnowledgeIngestItem] = Field(min_length=1, max_length=200)
    min_quality_score: float = Field(default=0.6, ge=0.0, le=1.0)
    created_by: str | None = None


class GatewayKnowledgeIngestResponse(BaseModel):
    received: int
    accepted: int
    rejected: int
    created_knowledge_ids: list[str] = Field(default_factory=list)
    rejected_items: list[PassiveRagIngestRejectedItem] = Field(default_factory=list)


class RagSummarizeToSkillRequest(BaseModel):
    scope: str = "team"
    limit: int = Field(default=20, ge=1, le=200)
    created_by: str | None = None


class RagSummarizeToSkillResponse(BaseModel):
    scope: str
    scanned: int
    generated_updates: int
    generated_update_ids: list[str] = Field(default_factory=list)
    detail: str | None = None


class AgentWorkflowRecord(BaseModel):
    workflow_id: str
    scope: str
    title: str
    source_knowledge_ids: list[str] = Field(default_factory=list)
    source_skill_update_ids: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    status: Literal["draft", "active", "optimized"] = "draft"
    optimization_count: int = 0
    created_at: datetime
    updated_at: datetime


class GenerateAgentWorkflowRequest(BaseModel):
    scope: str = "team"
    constraints: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None


class GenerateAgentWorkflowResponse(BaseModel):
    workflow: AgentWorkflowRecord
    detail: str | None = None


class OptimizeAgentWorkflowRequest(BaseModel):
    feedback_window: int = Field(default=20, ge=1, le=500)


class OptimizeAgentWorkflowResponse(BaseModel):
    workflow: AgentWorkflowRecord
    detail: str | None = None


class EvolutionOverviewResponse(BaseModel):
    skill_bundle_total: int
    team_rule_total: int
    gateway_knowledge_total: int
    rag_skill_update_total: int
    agent_workflow_total: int
    optimized_workflow_total: int


class EvolutionActionLogRecord(BaseModel):
    action_id: str
    action_name: str
    status: Literal["success", "failed"] = "success"
    actor: str | None = None
    detail: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ReplayEvolutionActionChainRequest(BaseModel):
    limit: int = Field(default=5, ge=1, le=30)


class ReplayEvolutionActionChainResponse(BaseModel):
    requested: int
    replayed: int
    skipped: int
    replayed_action_names: list[str] = Field(default_factory=list)
    skipped_action_names: list[str] = Field(default_factory=list)
    detail: str | None = None


class HookSecretStatusResponse(BaseModel):
    source: Literal["env", "db", "none"] = "none"
    masked_secret: str | None = None
    updated_at: datetime | None = None


class HookSecretRotateRequest(BaseModel):
    new_secret: str | None = None


class HookSecretRotateResponse(BaseModel):
    source: Literal["db"] = "db"
    new_secret: str
    masked_secret: str
    updated_at: datetime


class GitRepoPullSyncResponse(BaseModel):
    repo_id: str
    branch: str
    pulled: bool = False
    commit_sha: str | None = None
    scanned_files: int = 0
    imported_skills: int = 0
    conflicts: int = 0
    conflict_update_ids: list[str] = Field(default_factory=list)
    detail: str | None = None


# M1.3: Virtual Key Lifecycle - Audit Log and Usage Tracking
class KeyAuditLogEntry(BaseModel):
    """Single audit log entry for a virtual key"""
    timestamp: datetime
    action: Literal["issued", "used", "revoked", "expired"]
    user_id: str | None = None
    model_id: str | None = None
    tokens_used: int | None = None
    status: str | None = None
    details: dict[str, Any] | None = None


class KeyUsageStats(BaseModel):
    """Usage statistics for a virtual key"""
    key_id: str
    total_calls: int = 0
    total_tokens_used: int = 0
    calls_by_model: dict[str, int] = {}  # model_id -> call count
    tokens_by_model: dict[str, int] = {}  # model_id -> token count
    first_used_at: datetime | None = None
    last_used_at: datetime | None = None
    usage_by_hour: dict[str, int] = {}  # "YYYY-MM-DD HH:00" -> call count


class KeyAuditLogResponse(BaseModel):
    """Response for key audit log query"""
    key_id: str
    entries: list[KeyAuditLogEntry]
    total_entries: int
