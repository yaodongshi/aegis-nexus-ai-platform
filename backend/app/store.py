from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from collections import Counter
from itertools import count
import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
from time import perf_counter
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
import psycopg2
import yaml
from psycopg2.extras import Json

try:
    from qdrant_client import QdrantClient, models as qdrant_models
except Exception:  # pragma: no cover - optional runtime dependency
    QdrantClient = None  # type: ignore[assignment]
    qdrant_models = None  # type: ignore[assignment]

from .schemas import (
    ActionChainTemplateCreateRequest,
    ActionChainTemplateRecord,
    ActionChainTemplateRunRequest,
    ActionChainTemplateRunResponse,
    EvolutionOverviewResponse,
    EvolutionActionLogRecord,
    ReplayEvolutionActionChainRequest,
    ReplayEvolutionActionChainResponse,
    ApprovalRecord,
    ApprovalSubmitRequest,
    AgentWorkflowRecord,
    GatewayKnowledgeIngestRequest,
    GatewayKnowledgeIngestResponse,
    GenerateAgentWorkflowRequest,
    GenerateAgentWorkflowResponse,
    KeyIssueRequest,
    KeyIssueResponse,
    KeyRecord,
    ModelBatchRegisterRequest,
    ModelBatchRegisterResponse,
    ModelRecord,
    ModelBatchDeleteRequest,
    ModelBatchDeleteResponse,
    ModelRegisterRequest,
    ModelUpdateRequest,
    ProviderCreateRequest,
    ProviderBatchProbeItem,
    ProviderBatchProbeRequest,
    ProviderBatchProbeResponse,
    ProviderBatchDeleteRequest,
    ProviderBatchDeleteResponse,
    ProviderBatchUpdateRequest,
    ProviderBatchUpdateResponse,
    ProviderLiveModelDiscoveryRequest,
    ProviderLiveModelDiscoveryResponse,
    ProviderGatewaySyncResponse,
    ProviderProbeLogRecord,
    ProviderModelDiscoveryResponse,
    ProviderProbeRequest,
    ProviderProbeResponse,
    ProviderProbeResult,
    ProviderRecord,
    ProviderSyncRequest,
    ProviderUpdateRequest,
    RuntimeConfigApplyResponse,
    RuntimeConfigPreviewResponse,
    ClientRuntimeConfigResponse,
    GitRepoCreateRequest,
    GitRepoPullSyncResponse,
    HookSecretRotateResponse,
    HookSecretStatusResponse,
    GitRepoProbeResponse,
    GitRepoRecord,
    GitRepoUpdateRequest,
    PolicyRecord,
    PolicyUpsertRequest,
    PassiveRagIngestRejectedItem,
    PassiveRagIngestRequest,
    PassiveRagIngestResponse,
    OptimizeAgentWorkflowRequest,
    OptimizeAgentWorkflowResponse,
    RagSummarizeToSkillRequest,
    RagSummarizeToSkillResponse,
    SessionCreateRequest,
    SessionRecord,
    SessionUpdateRequest,
    SkillCreateRequest,
    SkillPackExportResponse,
    SkillPackFile,
    SkillHookReportRequest,
    SkillHookEventRecord,
    SkillHookReportResponse,
    SkillBundleRecord,
    SkillBundleUploadRequest,
    SkillBundleUploadResponse,
    SkillUpdateRequest,
    SkillRecord,
    SkillSearchStatusResponse,
    SkillUpdateRecord,
    SkillUpdateSyncRequest,
    TaskRunRecord,
    TaskRunReportRequest,
    TaskRunReportResponse,
    TeamSkillSyncApplyRequest,
    TeamSkillSyncApplyResponse,
    TeamSkillSyncRuleRecord,
    TeamSkillSyncRuleResponse,
    V2KeyPolicyRecord,
    V2KeyPolicyUpsertRequest,
    V2OwnershipViewItem,
    V2VirtualKeyCreateRequest,
    V2VirtualKeyRecord,
)


@dataclass
class PlatformStore:
    db_dsn: str | None = None
    models: dict[str, ModelRecord] = field(default_factory=dict)
    keys: dict[str, KeyRecord] = field(default_factory=dict)
    skills: dict[str, SkillRecord] = field(default_factory=dict)
    sessions: dict[str, SessionRecord] = field(default_factory=dict)
    task_runs: dict[str, TaskRunRecord] = field(default_factory=dict)
    skill_updates: dict[str, SkillUpdateRecord] = field(default_factory=dict)
    git_repos: dict[str, GitRepoRecord] = field(default_factory=dict)
    hook_events: dict[str, SkillHookReportResponse] = field(default_factory=dict)
    hook_secret_override: str | None = None
    hook_secret_updated_at: datetime | None = None
    policies: dict[str, PolicyRecord] = field(default_factory=dict)
    approvals: dict[str, ApprovalRecord] = field(default_factory=dict)
    providers: dict[str, ProviderRecord] = field(default_factory=dict)
    provider_secrets: dict[str, str] = field(default_factory=dict)
    provider_probe_logs: dict[str, list[ProviderProbeLogRecord]] = field(default_factory=dict)
    v2_virtual_keys: dict[str, V2VirtualKeyRecord] = field(default_factory=dict)
    v2_key_policies: dict[str, V2KeyPolicyRecord] = field(default_factory=dict)
    skill_bundles: dict[str, SkillBundleRecord] = field(default_factory=dict)
    team_skill_sync_rules: dict[str, TeamSkillSyncRuleRecord] = field(default_factory=dict)
    agent_workflows: dict[str, AgentWorkflowRecord] = field(default_factory=dict)
    evolution_action_logs: dict[str, EvolutionActionLogRecord] = field(default_factory=dict)
    action_chain_templates: dict[str, ActionChainTemplateRecord] = field(default_factory=dict)
    # M1.3: Virtual Key Lifecycle - Audit logging and usage tracking
    key_audit_logs: dict[str, list[dict]] = field(default_factory=dict)
    key_usage_stats: dict[str, dict] = field(default_factory=dict)
    _model_seq: count = field(default_factory=lambda: count(1))
    _key_seq: count = field(default_factory=lambda: count(1))
    _skill_seq: count = field(default_factory=lambda: count(1))
    _session_seq: count = field(default_factory=lambda: count(1))
    _task_run_seq: count = field(default_factory=lambda: count(1))
    _skill_update_seq: count = field(default_factory=lambda: count(1))
    _git_repo_seq: count = field(default_factory=lambda: count(1))
    _hook_event_seq: count = field(default_factory=lambda: count(1))
    _policy_seq: count = field(default_factory=lambda: count(1))
    _approval_seq: count = field(default_factory=lambda: count(1))
    _knowledge_seq: count = field(default_factory=lambda: count(1))
    _provider_seq: count = field(default_factory=lambda: count(1))
    _provider_probe_seq: count = field(default_factory=lambda: count(1))
    _v2_key_policy_seq: count = field(default_factory=lambda: count(1))
    _bundle_seq: count = field(default_factory=lambda: count(1))
    _rule_set_seq: count = field(default_factory=lambda: count(1))
    _workflow_seq: count = field(default_factory=lambda: count(1))
    _evolution_action_seq: count = field(default_factory=lambda: count(1))
    _action_template_seq: count = field(default_factory=lambda: count(1))
    _schema_ensured: bool = False
    _qdrant_client: Any | None = None
    _qdrant_init_attempted: bool = False
    _skill_embedding_available: bool | None = None
    _skill_embedding_last_error: str | None = None
    _skill_embedding_retry_after: datetime | None = None
    _skill_last_search_mode: str | None = None
    _skill_last_search_latency_ms: int | None = None
    _skill_last_search_result_count: int | None = None

    def __post_init__(self) -> None:
        if self.db_dsn is None:
            env_dsn = os.getenv("TEAM_AI_PLATFORM_DB_DSN", "").strip()
            self.db_dsn = env_dsn or None
        if self._db_enabled:
            try:
                self._ensure_schema_once()
            except Exception:  # DB not ready at startup — will retry on first request
                logging.getLogger(__name__).warning(
                    "DB schema init failed at startup; will retry on first request"
                )

    def seed_defaults(self) -> None:
        now = datetime.now(UTC)
        if self._db_enabled:
            self._ensure_schema_once()
            seeded_model = self.register_model(
                ModelRegisterRequest(
                    provider="openai",
                    provider_id=None,
                    upstream_model="gpt-4o",
                    name="GPT-4o",
                    endpoint="https://api.openai.com/v1/chat/completions",
                    context_window=128000,
                    cost_tier="high",
                    deployment_status="active",
                    tags=["chat", "code"],
                    labels={"team": "platform", "tier": "prod"},
                    quota=None,
                )
            )
            # Keep the bootstrap sample model disabled by default so runtime
            # model lists remain aligned with actually configured providers.
            self.update_model(
                seeded_model.id,
                ModelUpdateRequest(availability="disabled"),
            )
        elif not self.models:
            self.models["gpt-4o"] = ModelRecord(
                id="gpt-4o",
                provider="openai",
                provider_id=None,
                upstream_model="gpt-4o",
                name="GPT-4o",
                endpoint="https://api.openai.com/v1/chat/completions",
                context_window=128000,
                cost_tier="high",
                availability="active",
                deployment_status="active",
                tags=["chat", "code"],
                labels={"team": "platform", "tier": "prod"},
                quota=None,
                created_at=now,
                updated_at=now,
            )
        self.upsert_policy(
            PolicyUpsertRequest(
                name="default-approval",
                type="approval",
                rules={"actions": ["db_migrate", "prod_deploy"]},
                status="active",
            )
        )

    def list_models(
        self,
        *,
        provider: str | None = None,
        provider_id: str | None = None,
        availability: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ModelRecord]:
        if self._db_enabled:
            query = (
                "SELECT model_id, provider, provider_id, upstream_model, name, endpoint, "
                "context_window, cost_tier, availability, deployment_status, tags, labels, "
                "quota, created_at, updated_at "
                "FROM backend_models WHERE 1=1"
            )
            params: list[Any] = []
            if provider is not None:
                query += " AND provider = %s"
                params.append(provider)
            if provider_id is not None:
                query += " AND provider_id = %s"
                params.append(provider_id)
            if availability is not None:
                query += " AND availability = %s"
                params.append(availability)
            query += " ORDER BY created_at DESC"
            if limit is not None:
                query += " LIMIT %s"
                params.append(limit)
            if offset > 0:
                query += " OFFSET %s"
                params.append(offset)
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
            return [self._model_from_row(row) for row in rows]

        records = list(self.models.values())
        if provider is not None:
            records = [record for record in records if record.provider == provider]
        if provider_id is not None:
            records = [record for record in records if record.provider_id == provider_id]
        if availability is not None:
            records = [record for record in records if record.availability == availability]
        if offset > 0:
            records = records[offset:]
        if limit is not None:
            records = records[:limit]
        return records

    def register_model(self, payload: ModelRegisterRequest, *, sync_gateway: bool = True) -> ModelRecord:
        now = datetime.now(UTC)
        model_id = payload.name.lower().replace(" ", "-")
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_models (
                        model_id, provider, provider_id, upstream_model, name, endpoint,
                        context_window, cost_tier, availability, deployment_status,
                        tags, labels, quota, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (model_id) DO UPDATE SET
                        provider = EXCLUDED.provider,
                        provider_id = EXCLUDED.provider_id,
                        upstream_model = EXCLUDED.upstream_model,
                        name = EXCLUDED.name,
                        endpoint = EXCLUDED.endpoint,
                        context_window = EXCLUDED.context_window,
                        cost_tier = EXCLUDED.cost_tier,
                        availability = EXCLUDED.availability,
                        deployment_status = EXCLUDED.deployment_status,
                        tags = EXCLUDED.tags,
                        labels = EXCLUDED.labels,
                        quota = EXCLUDED.quota,
                        updated_at = EXCLUDED.updated_at
                    RETURNING model_id, provider, provider_id, upstream_model, name, endpoint,
                              context_window, cost_tier, availability, deployment_status,
                              tags, labels, quota, created_at, updated_at
                    """,
                    (
                        model_id,
                        payload.provider,
                        payload.provider_id,
                        payload.upstream_model,
                        payload.name,
                        payload.endpoint,
                        payload.context_window,
                        payload.cost_tier,
                        "active",
                        payload.deployment_status,
                        Json(payload.tags),
                        Json(payload.labels),
                        payload.quota,
                        now,
                        now,
                    ),
                )
                row = cur.fetchone()
            result = self._model_from_row(row)
            if sync_gateway:
                self._sync_providers_to_litellm_config()
            return result

        record = ModelRecord(
            id=model_id,
            provider=payload.provider,
            provider_id=payload.provider_id,
            upstream_model=payload.upstream_model,
            name=payload.name,
            endpoint=payload.endpoint,
            context_window=payload.context_window,
            cost_tier=payload.cost_tier,
            availability="active",
            deployment_status=payload.deployment_status,
            tags=payload.tags,
            labels=payload.labels,
            quota=payload.quota,
            created_at=now,
            updated_at=now,
        )
        self.models[model_id] = record
        if sync_gateway:
            self._sync_providers_to_litellm_config()
        return record

    def batch_register_models(self, payload: ModelBatchRegisterRequest) -> ModelBatchRegisterResponse:
        normalized_payloads: list[ModelRegisterRequest] = []
        seen_ids: set[str] = set()
        for item in payload.models:
            model_id = item.name.lower().replace(" ", "-")
            if model_id in seen_ids:
                continue
            seen_ids.add(model_id)
            normalized_payloads.append(item)

        if not normalized_payloads:
            return ModelBatchRegisterResponse(total=0, registered=0, skipped=0, items=[])

        records: list[ModelRecord] = []
        for item in normalized_payloads:
            records.append(self.register_model(item, sync_gateway=False))

        self._sync_providers_to_litellm_config()
        return ModelBatchRegisterResponse(
            total=len(payload.models),
            registered=len(records),
            skipped=len(payload.models) - len(records),
            items=records,
        )

    def get_model(self, model_id: str) -> ModelRecord | None:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                      SELECT model_id, provider, provider_id, upstream_model, name, endpoint,
                          context_window, cost_tier, availability, deployment_status,
                          tags, labels, quota, created_at, updated_at
                    FROM backend_models WHERE model_id = %s
                    """,
                    (model_id,),
                )
                row = cur.fetchone()
            return self._model_from_row(row) if row else None
        return self.models.get(model_id)

    def update_model(self, model_id: str, payload: ModelUpdateRequest) -> ModelRecord | None:
        if self._db_enabled:
            record = self.get_model(model_id)
            if record is None:
                return None
            data = payload.model_dump(exclude_none=True)
            updated = record.model_copy(update=data | {"updated_at": datetime.now(UTC)})
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_models SET
                        provider_id = %s,
                        upstream_model = %s,
                        endpoint = %s,
                        context_window = %s,
                        cost_tier = %s,
                        availability = %s,
                        deployment_status = %s,
                        tags = %s,
                        labels = %s,
                        quota = %s,
                        updated_at = %s
                    WHERE model_id = %s
                    """,
                    (
                        updated.provider_id,
                        updated.upstream_model,
                        updated.endpoint,
                        updated.context_window,
                        updated.cost_tier,
                        updated.availability,
                        updated.deployment_status,
                        Json(updated.tags),
                        Json(updated.labels),
                        updated.quota,
                        updated.updated_at,
                        model_id,
                    ),
                )
            self._sync_providers_to_litellm_config()
            return updated

        record = self.models.get(model_id)
        if record is None:
            return None
        updated = record.model_copy(update=payload.model_dump(exclude_none=True) | {"updated_at": datetime.now(UTC)})
        self.models[model_id] = updated
        self._sync_providers_to_litellm_config()
        return updated

    def delete_model(self, model_id: str) -> bool:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("DELETE FROM backend_models WHERE model_id = %s", (model_id,))
                deleted = cur.rowcount > 0
            if deleted:
                self._sync_providers_to_litellm_config()
            return deleted

        deleted = self.models.pop(model_id, None) is not None
        if deleted:
            self._sync_providers_to_litellm_config()
        return deleted

    def batch_delete_models(self, payload: ModelBatchDeleteRequest) -> ModelBatchDeleteResponse:
        normalized_ids = [str(model_id).strip() for model_id in payload.model_ids if str(model_id).strip()]
        unique_ids = list(dict.fromkeys(normalized_ids))
        if not unique_ids:
            return ModelBatchDeleteResponse(total=0, deleted=0, deleted_ids=[], missing_ids=[])

        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT model_id FROM backend_models WHERE model_id = ANY(%s)",
                    (unique_ids,),
                )
                existing_ids = {row[0] for row in cur.fetchall()}
                if existing_ids:
                    cur.execute(
                        "DELETE FROM backend_models WHERE model_id = ANY(%s)",
                        (sorted(existing_ids),),
                    )

            deleted_ids = sorted(existing_ids)
            missing_ids = sorted([model_id for model_id in unique_ids if model_id not in existing_ids])
            if deleted_ids:
                self._sync_providers_to_litellm_config()
            return ModelBatchDeleteResponse(
                total=len(unique_ids),
                deleted=len(deleted_ids),
                deleted_ids=deleted_ids,
                missing_ids=missing_ids,
            )

        existing_ids = {model_id for model_id in unique_ids if model_id in self.models}
        for model_id in existing_ids:
            self.models.pop(model_id, None)

        deleted_ids = sorted(existing_ids)
        missing_ids = sorted([model_id for model_id in unique_ids if model_id not in existing_ids])
        if deleted_ids:
            self._sync_providers_to_litellm_config()
        return ModelBatchDeleteResponse(
            total=len(unique_ids),
            deleted=len(deleted_ids),
            deleted_ids=deleted_ids,
            missing_ids=missing_ids,
        )

    # M1.1: Model alias methods
    def list_model_aliases(self, provider: str | None = None, tier: str | None = None) -> list[dict]:
        from .model_alias_presets import list_aliases
        presets = list_aliases(provider=provider, tier=tier)
        return [
            {
                "alias": p.alias,
                "real_model_id": p.real_model_id,
                "provider": p.provider,
                "tier": p.tier,
                "context_window": p.context_window,
                "description": p.description,
                "supported_capabilities": p.supported_capabilities,
                "cost_per_1m_input_tokens": p.cost_per_1m_input_tokens,
                "cost_per_1m_output_tokens": p.cost_per_1m_output_tokens,
            }
            for p in presets
        ]

    def get_model_by_alias(self, alias: str) -> dict | None:
        from .model_alias_presets import lookup_by_alias
        preset = lookup_by_alias(alias)
        if preset is None:
            return None
        return {
            "alias": preset.alias,
            "real_model_id": preset.real_model_id,
            "provider": preset.provider,
            "tier": preset.tier,
            "context_window": preset.context_window,
            "description": preset.description,
            "supported_capabilities": preset.supported_capabilities,
            "cost_per_1m_input_tokens": preset.cost_per_1m_input_tokens,
            "cost_per_1m_output_tokens": preset.cost_per_1m_output_tokens,
        }

    def get_alias_providers(self) -> list[str]:
        from .model_alias_presets import get_providers
        return get_providers()

    def get_alias_tiers(self) -> list[str]:
        from .model_alias_presets import get_tiers
        return get_tiers()

    # ------------------------------------------------------------------
    # LiteLLM key bridge helpers
    # ------------------------------------------------------------------

    def _generate_litellm_key(
        self,
        *,
        key_id: str,
        label: str | None,
        user_id: str | None,
        scope: str | None,
        quota: int | None,
        expire_at: Any,
        expires_days: int | None,
    ) -> tuple[str, str | None]:
        """调用 LiteLLM /key/generate，返回 (key_secret, litellm_key_id)。
        失败时回退到本地 sk-virtual- 前缀的 key，litellm_key_id 为 None。
        """
        litellm_base = self._litellm_base_url()
        litellm_master = self._litellm_master_key()
        if litellm_base and litellm_master:
            try:
                # 构建模型限制列表（scope 可能是 "gpt-4o,claude-3-5-sonnet" 或 "project:*"）
                model_list: list[str] = []
                if scope and scope != "project:*" and not scope.startswith("project:"):
                    model_list = [s.strip() for s in scope.split(",") if s.strip()]

                # 构建过期时间参数
                duration: str | None = None
                if expires_days:
                    duration = f"{expires_days}d"
                elif expire_at is not None:
                    from datetime import timezone as _tz
                    import math as _math
                    expire_dt = expire_at if hasattr(expire_at, "timestamp") else None
                    if expire_dt:
                        diff_seconds = expire_dt.timestamp() - datetime.now(_tz.utc).timestamp()
                        if diff_seconds > 0:
                            duration = f"{_math.ceil(diff_seconds)}s"

                request_body: dict[str, Any] = {
                    "key_alias": f"{label or 'key'}:{user_id or 'user'}:{key_id}",
                    "user_id": user_id or "unknown",
                    "metadata": {"team_ai_key_id": key_id, "platform": "team-ai"},
                }
                if model_list:
                    request_body["models"] = model_list
                if quota is not None:
                    # LiteLLM budget 单位是 USD，quota 单位是微分；简单折算 1 quota = 0.000001 USD
                    request_body["max_budget"] = float(quota) / 1_000_000
                if duration:
                    request_body["duration"] = duration

                with httpx.Client(timeout=10.0) as http_client:
                    resp = http_client.post(
                        f"{litellm_base}/key/generate",
                        headers={"Authorization": f"Bearer {litellm_master}"},
                        json=request_body,
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    real_key: str = data.get("key", "")
                    lk_id: str = data.get("key_id") or data.get("token_id") or data.get("id") or ""
                    if real_key:
                        return real_key, lk_id or None
            except Exception as exc:
                logging.getLogger(__name__).warning("LiteLLM key/generate failed, falling back to local key: %s", exc)

        # 回退：生成本地 key（无法通过 LiteLLM 网关路由）
        return f"sk-virtual-{uuid4().hex[:12]}", None

    def _delete_litellm_key(self, litellm_key_id: str) -> bool:
        """调用 LiteLLM /key/delete 撤销 key，返回是否成功。"""
        litellm_base = self._litellm_base_url()
        litellm_master = self._litellm_master_key()
        if not litellm_base or not litellm_master or not litellm_key_id:
            return False
        try:
            with httpx.Client(timeout=10.0) as http_client:
                resp = http_client.post(
                    f"{litellm_base}/key/delete",
                    headers={"Authorization": f"Bearer {litellm_master}"},
                    json={"keys": [litellm_key_id]},
                )
            return resp.status_code == 200
        except Exception as exc:
            logging.getLogger(__name__).warning("LiteLLM key/delete failed: %s", exc)
            return False

    def issue_key(self, payload: KeyIssueRequest) -> tuple[KeyRecord, KeyIssueResponse]:
        now = datetime.now(UTC)
        key_id = self._next_id("key")

        # --- 尝试从 LiteLLM 生成真实可用的 key ---
        key_secret, litellm_key_id = self._generate_litellm_key(
            key_id=key_id,
            label=payload.label,
            user_id=payload.user_id,
            scope=payload.scope,
            quota=payload.quota,
            expire_at=payload.expire_at,
            expires_days=getattr(payload, "expires_days", None),
        )
        key_hash = sha256(key_secret.encode("utf-8")).hexdigest()

        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_keys (
                        key_id, key_hash, label, user_id, project_id, scope,
                        expire_at, quota, status, created_at, updated_at, litellm_key_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active', %s, %s, %s)
                    RETURNING key_id, key_hash, label, user_id, project_id, scope,
                              expire_at, quota, status, created_at, updated_at, litellm_key_id
                    """,
                    (
                        key_id,
                        key_hash,
                        payload.label,
                        payload.user_id,
                        payload.project_id,
                        payload.scope,
                        payload.expire_at,
                        payload.quota,
                        now,
                        now,
                        litellm_key_id,
                    ),
                )
                row = cur.fetchone()
            record = self._key_from_row(row)
            # Also store in memory for audit/stats queries (M1.3 requirement)
            self.keys[key_id] = record
            self._record_audit_log(key_id, "issued", payload.user_id, {"label": payload.label, "scope": payload.scope})
            response = KeyIssueResponse(
                key_id=key_id,
                key_secret=key_secret,
                label=record.label,
                user_id=record.user_id,
                project_id=record.project_id,
                status=record.status,
                expire_at=record.expire_at,
            )
            return record, response

        record = KeyRecord(
            id=key_id,
            key_hash=key_hash,
            label=payload.label,
            user_id=payload.user_id,
            project_id=payload.project_id,
            scope=payload.scope,
            expire_at=payload.expire_at,
            quota=payload.quota,
            status="active",
            litellm_key_id=litellm_key_id,
            created_at=now,
            updated_at=now,
        )
        self.keys[key_id] = record
        self._record_audit_log(key_id, "issued", payload.user_id, {"label": payload.label, "scope": payload.scope})
        response = KeyIssueResponse(
            key_id=key_id,
            key_secret=key_secret,
            label=record.label,
            user_id=record.user_id,
            project_id=record.project_id,
            status=record.status,
            expire_at=record.expire_at,
        )
        return record, response

    def list_keys(
        self,
        *,
        user_id: str | None = None,
        project_id: str | None = None,
        status: str | None = None,
        q: str | None = None,
    ) -> list[KeyRecord]:
        self._ensure_schema_for_request()
        if self._db_enabled:
            query = (
                "SELECT key_id, key_hash, label, user_id, project_id, scope, "
                "expire_at, quota, status, created_at, updated_at, litellm_key_id "
                "FROM backend_keys WHERE 1=1"
            )
            params: list[Any] = []
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
            if project_id is not None:
                query += " AND project_id = %s"
                params.append(project_id)
            if status is not None:
                query += " AND status = %s"
                params.append(status)
            if q is not None:
                query += " AND (key_id ILIKE %s OR label ILIKE %s OR user_id ILIKE %s OR project_id ILIKE %s)"
                like = f"%{q}%"
                params.extend([like, like, like, like])
            query += " ORDER BY created_at DESC"
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
            return [self._key_from_row(row) for row in rows]

        records = list(self.keys.values())
        if user_id is not None:
            records = [r for r in records if r.user_id == user_id]
        if project_id is not None:
            records = [r for r in records if r.project_id == project_id]
        if status is not None:
            records = [r for r in records if r.status == status]
        if q is not None:
            q_lower = q.lower()
            records = [
                r for r in records
                if q_lower in (r.id or "").lower()
                or q_lower in (r.user_id or "").lower()
                or q_lower in (r.project_id or "").lower()
            ]
        return records

    def revoke_key(self, key_id: str) -> KeyRecord | None:
        if self._db_enabled:
            updated_at = datetime.now(UTC)
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_keys
                    SET status = 'revoked', updated_at = %s
                    WHERE key_id = %s
                    RETURNING key_id, key_hash, label, user_id, project_id, scope,
                              expire_at, quota, status, created_at, updated_at, litellm_key_id
                    """,
                    (updated_at, key_id),
                )
                row = cur.fetchone()
            record = self._key_from_row(row) if row else None
            if record is not None:
                self.keys[key_id] = record
                self._record_audit_log(key_id, "revoked", None, {})
                # 同步撤销 LiteLLM 侧的 key
                if record.litellm_key_id:
                    self._delete_litellm_key(record.litellm_key_id)
            return record

        record = self.keys.get(key_id)
        if record is None:
            return None
        # 同步撤销 LiteLLM 侧的 key
        if record.litellm_key_id:
            self._delete_litellm_key(record.litellm_key_id)
        updated = record.model_copy(update={"status": "revoked", "updated_at": datetime.now(UTC)})
        self.keys[key_id] = updated
        self._record_audit_log(key_id, "revoked", None, {})
        return updated

    def create_v2_virtual_key(self, payload: V2VirtualKeyCreateRequest) -> tuple[V2VirtualKeyRecord, str]:
        now = datetime.now(UTC)
        key_id = self._next_id("key")
        key_secret = f"sk-v2-{uuid4().hex}"
        key_hash = sha256(key_secret.encode("utf-8")).hexdigest()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO cp_virtual_keys (
                        key_id, key_hash, team_id, alias, owner_type, owner_id, status,
                        expires_at, rotated_from, created_at, updated_at, revoked_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'active', %s, NULL, %s, %s, NULL)
                    RETURNING key_id, team_id, alias, owner_type, owner_id, status,
                              expires_at, rotated_from, created_at, updated_at, revoked_at
                    """,
                    (
                        key_id,
                        key_hash,
                        payload.team_id,
                        payload.alias,
                        payload.owner_type,
                        payload.owner_id,
                        payload.expires_at,
                        now,
                        now,
                    ),
                )
                row = cur.fetchone()
            return self._v2_virtual_key_from_row(row), key_secret

        record = V2VirtualKeyRecord(
            key_id=key_id,
            team_id=payload.team_id,
            alias=payload.alias,
            owner_type=payload.owner_type,
            owner_id=payload.owner_id,
            status="active",
            expires_at=payload.expires_at,
            rotated_from=None,
            created_at=now,
            updated_at=now,
            revoked_at=None,
        )
        self.v2_virtual_keys[key_id] = record
        return record, key_secret

    def list_v2_virtual_keys(
        self,
        team_id: str | None = None,
        owner_type: str | None = None,
        owner_id: str | None = None,
        status: str | None = None,
    ) -> list[V2VirtualKeyRecord]:
        if self._db_enabled:
            where = []
            args: list[Any] = []
            if team_id:
                where.append("team_id = %s")
                args.append(team_id)
            if owner_type:
                where.append("owner_type = %s")
                args.append(owner_type)
            if owner_id:
                where.append("owner_id = %s")
                args.append(owner_id)
            if status:
                where.append("status = %s")
                args.append(status)

            where_sql = f"WHERE {' AND '.join(where)}" if where else ""
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT key_id, team_id, alias, owner_type, owner_id, status,
                           expires_at, rotated_from, created_at, updated_at, revoked_at
                    FROM cp_virtual_keys
                    {where_sql}
                    ORDER BY created_at DESC
                    """,
                    tuple(args),
                )
                rows = cur.fetchall()
            return [self._v2_virtual_key_from_row(row) for row in rows]

        records = list(self.v2_virtual_keys.values())
        if team_id:
            records = [record for record in records if record.team_id == team_id]
        if owner_type:
            records = [record for record in records if record.owner_type == owner_type]
        if owner_id:
            records = [record for record in records if record.owner_id == owner_id]
        if status:
            records = [record for record in records if record.status == status]
        return sorted(records, key=lambda item: item.created_at, reverse=True)

    def list_v2_ownership_views(
        self,
        team_id: str | None = None,
        owner_type: str | None = None,
        owner_id: str | None = None,
    ) -> list[V2OwnershipViewItem]:
        if self._db_enabled:
            where = []
            args: list[Any] = []
            if team_id:
                where.append("team_id = %s")
                args.append(team_id)
            if owner_type:
                where.append("owner_type = %s")
                args.append(owner_type)
            if owner_id:
                where.append("owner_id = %s")
                args.append(owner_id)

            where_sql = f"WHERE {' AND '.join(where)}" if where else ""
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        team_id,
                        owner_type,
                        owner_id,
                        COUNT(*)::INT AS total_keys,
                        SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END)::INT AS active_keys,
                        SUM(CASE WHEN status = 'revoked' THEN 1 ELSE 0 END)::INT AS revoked_keys,
                        MAX(updated_at) AS last_updated_at
                    FROM cp_virtual_keys
                    {where_sql}
                    GROUP BY team_id, owner_type, owner_id
                    ORDER BY total_keys DESC, team_id, owner_type, owner_id
                    """,
                    tuple(args),
                )
                rows = cur.fetchall()
            return [
                V2OwnershipViewItem(
                    team_id=row[0],
                    owner_type=row[1],
                    owner_id=row[2],
                    total_keys=row[3],
                    active_keys=row[4],
                    revoked_keys=row[5],
                    last_updated_at=row[6],
                )
                for row in rows
            ]

        grouped: dict[tuple[str, str, str], list[V2VirtualKeyRecord]] = {}
        for record in self.v2_virtual_keys.values():
            key = (record.team_id, record.owner_type, record.owner_id)
            grouped.setdefault(key, []).append(record)

        items: list[V2OwnershipViewItem] = []
        for (item_team_id, item_owner_type, item_owner_id), records in grouped.items():
            if team_id and item_team_id != team_id:
                continue
            if owner_type and item_owner_type != owner_type:
                continue
            if owner_id and item_owner_id != owner_id:
                continue
            active_count = len([r for r in records if r.status == "active"])
            revoked_count = len([r for r in records if r.status == "revoked"])
            last_updated_at = max((r.updated_at for r in records), default=None)
            items.append(
                V2OwnershipViewItem(
                    team_id=item_team_id,
                    owner_type=item_owner_type,
                    owner_id=item_owner_id,
                    total_keys=len(records),
                    active_keys=active_count,
                    revoked_keys=revoked_count,
                    last_updated_at=last_updated_at,
                )
            )

        return sorted(items, key=lambda item: (item.total_keys, item.team_id, item.owner_type, item.owner_id), reverse=True)

    def get_v2_virtual_key(self, key_id: str) -> V2VirtualKeyRecord | None:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT key_id, team_id, alias, owner_type, owner_id, status,
                           expires_at, rotated_from, created_at, updated_at, revoked_at
                    FROM cp_virtual_keys
                    WHERE key_id = %s
                    """,
                    (key_id,),
                )
                row = cur.fetchone()
            return self._v2_virtual_key_from_row(row) if row else None
        return self.v2_virtual_keys.get(key_id)

    def revoke_v2_virtual_key(self, key_id: str) -> V2VirtualKeyRecord | None:
        now = datetime.now(UTC)
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE cp_virtual_keys
                    SET status = 'revoked', updated_at = %s, revoked_at = %s
                    WHERE key_id = %s
                    RETURNING key_id, team_id, alias, owner_type, owner_id, status,
                              expires_at, rotated_from, created_at, updated_at, revoked_at
                    """,
                    (now, now, key_id),
                )
                row = cur.fetchone()
            return self._v2_virtual_key_from_row(row) if row else None

        record = self.v2_virtual_keys.get(key_id)
        if record is None:
            return None
        updated = record.model_copy(update={"status": "revoked", "updated_at": now, "revoked_at": now})
        self.v2_virtual_keys[key_id] = updated
        return updated

    def rotate_v2_virtual_key(self, key_id: str) -> tuple[V2VirtualKeyRecord, str] | None:
        old_key = self.get_v2_virtual_key(key_id)
        if old_key is None:
            return None
        self.revoke_v2_virtual_key(key_id)
        new_key, new_secret = self.create_v2_virtual_key(
            V2VirtualKeyCreateRequest(
                team_id=old_key.team_id,
                alias=old_key.alias,
                owner_type=old_key.owner_type,
                owner_id=old_key.owner_id,
                expires_at=old_key.expires_at,
            )
        )
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE cp_virtual_keys
                    SET rotated_from = %s
                    WHERE key_id = %s
                    RETURNING key_id, team_id, alias, owner_type, owner_id, status,
                              expires_at, rotated_from, created_at, updated_at, revoked_at
                    """,
                    (key_id, new_key.key_id),
                )
                row = cur.fetchone()
            return self._v2_virtual_key_from_row(row), new_secret

        updated = new_key.model_copy(update={"rotated_from": key_id})
        self.v2_virtual_keys[updated.key_id] = updated
        return updated, new_secret

    def upsert_v2_key_policy(self, key_id: str, payload: V2KeyPolicyUpsertRequest) -> V2KeyPolicyRecord | None:
        now = datetime.now(UTC)
        if self.get_v2_virtual_key(key_id) is None:
            return None
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT policy_id
                    FROM cp_key_policies
                    WHERE key_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (key_id,),
                )
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """
                        UPDATE cp_key_policies
                        SET allowed_models = %s,
                            denied_models = %s,
                            quota_tokens_day = %s,
                            quota_tokens_month = %s,
                            rate_limit_rpm = %s,
                            burst_limit = %s,
                            emergency_block = %s,
                            updated_at = %s
                        WHERE policy_id = %s
                        RETURNING policy_id, key_id, allowed_models, denied_models,
                                  quota_tokens_day, quota_tokens_month, rate_limit_rpm,
                                  burst_limit, emergency_block, effective_from, effective_to,
                                  created_at, updated_at
                        """,
                        (
                            payload.allowed_models,
                            payload.denied_models,
                            payload.quota_tokens_day,
                            payload.quota_tokens_month,
                            payload.rate_limit_rpm,
                            payload.burst_limit,
                            payload.emergency_block,
                            now,
                            existing[0],
                        ),
                    )
                    row = cur.fetchone()
                else:
                    cur.execute(
                        """
                        INSERT INTO cp_key_policies (
                            policy_id, key_id, allowed_models, denied_models,
                            quota_tokens_day, quota_tokens_month, rate_limit_rpm,
                            burst_limit, emergency_block, effective_from, effective_to,
                            created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s)
                        RETURNING policy_id, key_id, allowed_models, denied_models,
                                  quota_tokens_day, quota_tokens_month, rate_limit_rpm,
                                  burst_limit, emergency_block, effective_from, effective_to,
                                  created_at, updated_at
                        """,
                        (
                            self._next_id("v2policy"),
                            key_id,
                            payload.allowed_models,
                            payload.denied_models,
                            payload.quota_tokens_day,
                            payload.quota_tokens_month,
                            payload.rate_limit_rpm,
                            payload.burst_limit,
                            payload.emergency_block,
                            now,
                            now,
                            now,
                        ),
                    )
                    row = cur.fetchone()
            return self._v2_key_policy_from_row(row)

        existing = self.v2_key_policies.get(key_id)
        policy_id = existing.policy_id if existing else self._next_id("v2policy")
        created_at = existing.created_at if existing else now
        record = V2KeyPolicyRecord(
            policy_id=policy_id,
            key_id=key_id,
            allowed_models=payload.allowed_models,
            denied_models=payload.denied_models,
            quota_tokens_day=payload.quota_tokens_day,
            quota_tokens_month=payload.quota_tokens_month,
            rate_limit_rpm=payload.rate_limit_rpm,
            burst_limit=payload.burst_limit,
            emergency_block=payload.emergency_block,
            effective_from=existing.effective_from if existing else now,
            effective_to=None,
            created_at=created_at,
            updated_at=now,
        )
        self.v2_key_policies[key_id] = record
        return record

    def get_v2_key_policy(self, key_id: str) -> V2KeyPolicyRecord | None:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT policy_id, key_id, allowed_models, denied_models,
                           quota_tokens_day, quota_tokens_month, rate_limit_rpm,
                           burst_limit, emergency_block, effective_from, effective_to,
                           created_at, updated_at
                    FROM cp_key_policies WHERE key_id = %s
                    """,
                    (key_id,),
                )
                row = cur.fetchone()
            return self._v2_key_policy_from_row(row) if row else None
        return self.v2_key_policies.get(key_id)

    # M1.3: Audit log and usage tracking methods
    def _record_audit_log(self, key_id: str, action: str, user_id: str | None, details: dict) -> None:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "user_id": user_id,
            "details": details,
        }
        if key_id not in self.key_audit_logs:
            self.key_audit_logs[key_id] = []
        self.key_audit_logs[key_id].append(entry)

    def _update_usage_stats(self, key_id: str, model_id: str, tokens_used: int) -> None:
        if key_id not in self.key_usage_stats:
            self.key_usage_stats[key_id] = {
                "total_calls": 0,
                "total_tokens_used": 0,
                "calls_by_model": {},
                "tokens_by_model": {},
                "first_used_at": None,
                "last_used_at": None,
            }
        stats = self.key_usage_stats[key_id]
        now_str = datetime.now(UTC).isoformat()
        stats["total_calls"] += 1
        stats["total_tokens_used"] += tokens_used
        stats["calls_by_model"][model_id] = stats["calls_by_model"].get(model_id, 0) + 1
        stats["tokens_by_model"][model_id] = stats["tokens_by_model"].get(model_id, 0) + tokens_used
        if stats["first_used_at"] is None:
            stats["first_used_at"] = now_str
        stats["last_used_at"] = now_str

    def get_key_audit_log(self, key_id: str, limit: int | None = None) -> list[dict] | None:
        if key_id not in self.keys:
            return None
        entries = self.key_audit_logs.get(key_id, [])
        if limit is not None:
            entries = entries[-limit:]
        return entries

    def get_key_usage_stats(self, key_id: str) -> dict | None:
        if key_id not in self.keys:
            return None
        return self.key_usage_stats.get(key_id, {
            "total_calls": 0,
            "total_tokens_used": 0,
            "calls_by_model": {},
            "tokens_by_model": {},
            "first_used_at": None,
            "last_used_at": None,
        })

    def create_skill(self, payload: SkillCreateRequest) -> SkillRecord:
        now = datetime.now(UTC)
        skill_id = self._next_id("skill")
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_skills (
                        skill_id, name, description, system_prompt, category, tags,
                        version, owner_id, status, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, '1.0', NULL, 'active', %s, %s)
                    RETURNING skill_id, name, description, system_prompt, category, tags,
                              status, created_at, updated_at
                    """,
                    (
                        skill_id,
                        payload.name,
                        payload.description,
                        payload.system_prompt,
                        payload.category,
                        Json(payload.tags),
                        now,
                        now,
                    ),
                )
                row = cur.fetchone()
            record = self._skill_from_row(row)
            self._upsert_skill_vector(record)
            return record

        record = SkillRecord(
            id=skill_id,
            name=payload.name,
            description=payload.description,
            system_prompt=payload.system_prompt,
            category=payload.category,
            tags=payload.tags,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.skills[skill_id] = record
        self._upsert_skill_vector(record)
        return record

    def delete_skill(self, skill_id: str) -> bool:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("DELETE FROM backend_skills WHERE skill_id = %s", (skill_id,))
                deleted = cur.rowcount > 0
            self.skills.pop(skill_id, None)
            if deleted:
                self._delete_skill_vector(skill_id)
            return deleted
        existed = skill_id in self.skills
        self.skills.pop(skill_id, None)
        if existed:
            self._delete_skill_vector(skill_id)
        return existed

    def list_skills(self) -> list[SkillRecord]:
        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT skill_id, name, description, system_prompt, category, tags,
                           status, created_at, updated_at
                    FROM backend_skills ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()
            return [self._skill_from_row(row) for row in rows]
        return list(self.skills.values())

    def get_skill(self, skill_id: str) -> SkillRecord | None:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT skill_id, name, description, system_prompt, category, tags,
                           status, created_at, updated_at
                    FROM backend_skills WHERE skill_id = %s
                    """,
                    (skill_id,),
                )
                row = cur.fetchone()
            return self._skill_from_row(row) if row else None
        return self.skills.get(skill_id)

    def update_skill(self, skill_id: str, payload: SkillUpdateRequest) -> SkillRecord | None:
        now = datetime.now(UTC)
        patch = payload.model_dump(exclude_none=True)
        if not patch:
            return self.get_skill(skill_id)

        if self._db_enabled:
            current = self.get_skill(skill_id)
            if current is None:
                return None

            next_name = patch.get("name", current.name)
            next_description = patch.get("description", current.description)
            next_system_prompt = patch.get("system_prompt", current.system_prompt)
            next_category = patch.get("category", current.category)
            next_tags = patch.get("tags", current.tags)
            next_status = patch.get("status", current.status)

            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_skills
                    SET name = %s,
                        description = %s,
                        system_prompt = %s,
                        category = %s,
                        tags = %s,
                        status = %s,
                        updated_at = %s
                    WHERE skill_id = %s
                    RETURNING skill_id, name, description, system_prompt, category, tags,
                              status, created_at, updated_at
                    """,
                    (
                        next_name,
                        next_description,
                        next_system_prompt,
                        next_category,
                        Json(next_tags),
                        next_status,
                        now,
                        skill_id,
                    ),
                )
                row = cur.fetchone()

            if row is None:
                return None
            updated = self._skill_from_row(row)
            self._upsert_skill_vector(updated)
            return updated

        current = self.skills.get(skill_id)
        if current is None:
            return None

        updated = current.model_copy(update={**patch, "updated_at": now})
        self.skills[skill_id] = updated
        self._upsert_skill_vector(updated)
        return updated

    def list_git_repos(self) -> list[GitRepoRecord]:
        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT git_repo_id, name, path, branch, auto_commit, is_active,
                           last_synced_at, created_at, updated_at
                    FROM backend_git_repos
                    ORDER BY is_active DESC, created_at DESC
                    """
                )
                rows = cur.fetchall()
            return [self._git_repo_from_row(row) for row in rows]

        return sorted(
            self.git_repos.values(),
            key=lambda item: (item.is_active, item.created_at),
            reverse=True,
        )

    def get_git_repo(self, repo_id: str) -> GitRepoRecord | None:
        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT git_repo_id, name, path, branch, auto_commit, is_active,
                           last_synced_at, created_at, updated_at
                    FROM backend_git_repos
                    WHERE git_repo_id = %s
                    """,
                    (repo_id,),
                )
                row = cur.fetchone()
            return self._git_repo_from_row(row) if row else None

        return self.git_repos.get(repo_id)

    def get_active_git_repo(self) -> GitRepoRecord | None:
        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT git_repo_id, name, path, branch, auto_commit, is_active,
                           last_synced_at, created_at, updated_at
                    FROM backend_git_repos
                    WHERE is_active = TRUE
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
            return self._git_repo_from_row(row) if row else None

        for item in self.git_repos.values():
            if item.is_active:
                return item
        return None

    def create_git_repo(self, payload: GitRepoCreateRequest) -> GitRepoRecord:
        self._ensure_schema_for_request()
        now = datetime.now(UTC)
        repo_id = self._next_id("gitrepo")
        repo_path = str(Path(payload.path).expanduser().resolve())

        if any(item.path == repo_path for item in self.list_git_repos()):
            raise ValueError("Git repository path already exists")

        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                if payload.make_active:
                    cur.execute("UPDATE backend_git_repos SET is_active = FALSE")
                cur.execute(
                    """
                    INSERT INTO backend_git_repos (
                        git_repo_id, name, path, branch, auto_commit,
                        is_active, last_synced_at, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s)
                    RETURNING git_repo_id, name, path, branch, auto_commit, is_active,
                              last_synced_at, created_at, updated_at
                    """,
                    (
                        repo_id,
                        payload.name.strip(),
                        repo_path,
                        payload.branch.strip() or "main",
                        payload.auto_commit,
                        payload.make_active,
                        now,
                        now,
                    ),
                )
                row = cur.fetchone()
            return self._git_repo_from_row(row)

        if payload.make_active:
            for existing in list(self.git_repos.values()):
                self.git_repos[existing.id] = existing.model_copy(update={"is_active": False, "updated_at": now})

        record = GitRepoRecord(
            id=repo_id,
            name=payload.name.strip(),
            path=repo_path,
            branch=payload.branch.strip() or "main",
            auto_commit=payload.auto_commit,
            is_active=payload.make_active,
            last_synced_at=None,
            created_at=now,
            updated_at=now,
        )
        self.git_repos[repo_id] = record
        return record

    def update_git_repo(self, repo_id: str, payload: GitRepoUpdateRequest) -> GitRepoRecord | None:
        self._ensure_schema_for_request()
        now = datetime.now(UTC)

        if self._db_enabled:
            existing = self.get_git_repo(repo_id)
            if existing is None:
                return None
            next_name = (payload.name or existing.name).strip()
            next_path = str(Path(payload.path).expanduser().resolve()) if payload.path else existing.path
            next_branch = (payload.branch or existing.branch).strip() or "main"
            next_auto_commit = existing.auto_commit if payload.auto_commit is None else payload.auto_commit
            for item in self.list_git_repos():
                if item.id != repo_id and item.path == next_path:
                    raise ValueError("Git repository path already exists")

            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_git_repos
                    SET name = %s,
                        path = %s,
                        branch = %s,
                        auto_commit = %s,
                        updated_at = %s
                    WHERE git_repo_id = %s
                    RETURNING git_repo_id, name, path, branch, auto_commit, is_active,
                              last_synced_at, created_at, updated_at
                    """,
                    (next_name, next_path, next_branch, next_auto_commit, now, repo_id),
                )
                row = cur.fetchone()
            return self._git_repo_from_row(row) if row else None

        existing = self.git_repos.get(repo_id)
        if existing is None:
            return None

        next_path = str(Path(payload.path).expanduser().resolve()) if payload.path else existing.path
        for item in self.git_repos.values():
            if item.id != repo_id and item.path == next_path:
                raise ValueError("Git repository path already exists")

        updated = existing.model_copy(
            update={
                "name": (payload.name or existing.name).strip(),
                "path": next_path,
                "branch": (payload.branch or existing.branch).strip() or "main",
                "auto_commit": existing.auto_commit if payload.auto_commit is None else payload.auto_commit,
                "updated_at": now,
            }
        )
        self.git_repos[repo_id] = updated
        return updated

    def activate_git_repo(self, repo_id: str) -> GitRepoRecord | None:
        self._ensure_schema_for_request()
        now = datetime.now(UTC)

        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("UPDATE backend_git_repos SET is_active = FALSE")
                cur.execute(
                    """
                    UPDATE backend_git_repos
                    SET is_active = TRUE,
                        updated_at = %s
                    WHERE git_repo_id = %s
                    RETURNING git_repo_id, name, path, branch, auto_commit, is_active,
                              last_synced_at, created_at, updated_at
                    """,
                    (now, repo_id),
                )
                row = cur.fetchone()
            return self._git_repo_from_row(row) if row else None

        if repo_id not in self.git_repos:
            return None
        for existing in list(self.git_repos.values()):
            self.git_repos[existing.id] = existing.model_copy(update={"is_active": False, "updated_at": now})
        active = self.git_repos[repo_id].model_copy(update={"is_active": True, "updated_at": now})
        self.git_repos[repo_id] = active
        return active

    def delete_git_repo(self, repo_id: str) -> bool:
        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("DELETE FROM backend_git_repos WHERE git_repo_id = %s", (repo_id,))
                return cur.rowcount > 0

        existed = repo_id in self.git_repos
        self.git_repos.pop(repo_id, None)
        return existed

    def probe_git_repo(self, repo_id: str) -> GitRepoProbeResponse | None:
        repo = self.get_git_repo(repo_id)
        if repo is None:
            return None

        repo_path = Path(repo.path).expanduser().resolve()
        path_exists = repo_path.exists()
        is_git_repo = (repo_path / ".git").exists()
        git_available = shutil.which("git") is not None
        active_branch: str | None = None
        configured_branch_exists = False
        error: str | None = None

        if git_available and is_git_repo:
            try:
                active_proc = subprocess.run(
                    ["git", "-C", str(repo_path), "branch", "--show-current"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                active_branch = (active_proc.stdout or "").strip() or None

                exists_proc = subprocess.run(
                    ["git", "-C", str(repo_path), "rev-parse", "--verify", repo.branch],
                    capture_output=True,
                    text=True,
                )
                configured_branch_exists = exists_proc.returncode == 0
            except Exception as exc:
                error = str(exc)
        elif path_exists and not is_git_repo:
            error = "Path exists but is not a git repository"
        elif not path_exists:
            error = "Path does not exist"

        return GitRepoProbeResponse(
            repo_id=repo.id,
            path=repo.path,
            path_exists=path_exists,
            is_git_repo=is_git_repo,
            git_available=git_available,
            configured_branch=repo.branch,
            active_branch=active_branch,
            configured_branch_exists=configured_branch_exists,
            error=error,
        )

    def report_skill_hook_event(
        self,
        payload: SkillHookReportRequest,
        *,
        idempotency_key: str,
    ) -> SkillHookReportResponse:
        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT hook_event_id, idempotency_key, linked_skill_ids
                    FROM backend_skill_hook_events
                    WHERE idempotency_key = %s
                    """,
                    (idempotency_key,),
                )
                row = cur.fetchone()
                if row:
                    linked_skill_ids = row[2] if isinstance(row[2], list) else []
                    return SkillHookReportResponse(
                        hook_event_id=row[0],
                        idempotency_key=row[1],
                        created=False,
                        linked_skill_ids=[str(item) for item in linked_skill_ids],
                        detail="Duplicate event ignored by idempotency key",
                    )

                hook_event_id = (payload.event_id or "").strip() or self._next_id("hookevent")
                linked_skill_ids = self._resolve_skill_ids_from_changed_files(payload.changed_files)
                now = datetime.now(UTC)
                cur.execute(
                    """
                    INSERT INTO backend_skill_hook_events (
                        hook_event_id, event_id, idempotency_key, repo_id, repository,
                        branch, commit_sha, changed_files, linked_skill_ids,
                        author, event_time, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        hook_event_id,
                        payload.event_id,
                        idempotency_key,
                        payload.repo_id,
                        payload.repository,
                        payload.branch,
                        payload.commit_sha,
                        Json(payload.changed_files),
                        Json(linked_skill_ids),
                        payload.author,
                        payload.event_time,
                        now,
                    ),
                )
            return SkillHookReportResponse(
                hook_event_id=hook_event_id,
                idempotency_key=idempotency_key,
                created=True,
                linked_skill_ids=linked_skill_ids,
            )

        existing = self.hook_events.get(idempotency_key)
        if existing:
            return existing.model_copy(update={"created": False, "detail": "Duplicate event ignored by idempotency key"})

        hook_event_id = (payload.event_id or "").strip() or self._next_id("hookevent")
        linked_skill_ids = self._resolve_skill_ids_from_changed_files(payload.changed_files)
        response = SkillHookReportResponse(
            hook_event_id=hook_event_id,
            idempotency_key=idempotency_key,
            created=True,
            linked_skill_ids=linked_skill_ids,
        )
        self.hook_events[idempotency_key] = response
        return response

    def list_skill_hook_events(self, limit: int = 50, offset: int = 0) -> list[SkillHookEventRecord]:
        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT hook_event_id, event_id, idempotency_key, repo_id, repository,
                           branch, commit_sha, changed_files, linked_skill_ids,
                           author, event_time, created_at
                    FROM backend_skill_hook_events
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
                rows = cur.fetchall()
            return [self._hook_event_from_row(row) for row in rows]

        records = sorted(self.hook_events.values(), key=lambda item: item.hook_event_id, reverse=True)
        paged = records[offset : offset + limit]
        now = datetime.now(UTC)
        return [
            SkillHookEventRecord(
                hook_event_id=item.hook_event_id,
                idempotency_key=item.idempotency_key,
                repository="local",
                branch="main",
                commit_sha="unknown",
                linked_skill_ids=item.linked_skill_ids,
                created_at=now,
            )
            for item in paged
        ]

    def ingest_passive_rag_items(self, payload: PassiveRagIngestRequest) -> PassiveRagIngestResponse:
        created_ids: list[str] = []
        rejected_items: list[PassiveRagIngestRejectedItem] = []
        seen_source_keys: set[str] = set()
        created_by = (payload.created_by or "system").strip() or "system"

        for item in payload.items:
            source_key = f"{item.source_type}:{item.source_id}"
            if source_key in seen_source_keys:
                rejected_items.append(
                    PassiveRagIngestRejectedItem(source_id=item.source_id, reason="duplicate_source_in_batch")
                )
                continue
            seen_source_keys.add(source_key)

            content = (item.content or "").strip()
            if not content:
                rejected_items.append(
                    PassiveRagIngestRejectedItem(source_id=item.source_id, reason="empty_content")
                )
                continue

            if item.quality_score < payload.min_quality_score:
                rejected_items.append(
                    PassiveRagIngestRejectedItem(source_id=item.source_id, reason="quality_below_threshold")
                )
                continue

            title = (item.title or f"[{item.source_type}] {item.source_id}").strip()
            project_id = (item.project_id or "proj_passive_rag").strip() or "proj_passive_rag"

            tags = set(item.tags)
            tags.add("passive-rag")
            tags.add(f"source:{item.source_type}")
            if item.repository:
                tags.add(f"repo:{item.repository}")

            metadata_content = ""
            if item.metadata:
                metadata_content = (
                    "\n\n---\n"
                    "source_metadata:\n"
                    f"{json.dumps(item.metadata, ensure_ascii=False, sort_keys=True)}"
                )

            record = self.create_knowledge(
                project_id=project_id,
                title=title,
                content=f"{content}{metadata_content}",
                fmt="markdown",
                tags=sorted(tags),
                created_by=created_by,
            )
            created_ids.append(record.id)

        return PassiveRagIngestResponse(
            received=len(payload.items),
            accepted=len(created_ids),
            rejected=len(rejected_items),
            created_knowledge_ids=created_ids,
            rejected_items=rejected_items,
        )

    def upload_skill_bundle(self, payload: SkillBundleUploadRequest) -> SkillBundleUploadResponse:
        now = datetime.now(UTC)
        bundle_id = self._next_id("bundle")
        record = SkillBundleRecord(
            bundle_id=bundle_id,
            team_id=payload.team_id,
            skill_id=payload.skill_id,
            version=payload.version,
            tags=sorted(set(payload.tags)),
            uploaded_by=(payload.uploaded_by or "system").strip() or "system",
            created_at=now,
            updated_at=now,
        )
        self.skill_bundles[record.bundle_id] = record

        # 如果 bundle 中带有技能主体内容，则直接更新技能，便于团队下载后立即生效。
        bundle_skill = payload.bundle.get("skill") if isinstance(payload.bundle, dict) else None
        if isinstance(bundle_skill, dict):
            try:
                existing = self.get_skill(payload.skill_id)
                if existing:
                    self.update_skill(
                        payload.skill_id,
                        SkillUpdateRequest(
                            name=bundle_skill.get("name") or existing.name,
                            description=bundle_skill.get("description") or existing.description,
                            system_prompt=bundle_skill.get("system_prompt") or existing.system_prompt,
                            category=bundle_skill.get("category") or existing.category,
                            tags=bundle_skill.get("tags") or existing.tags,
                        ),
                    )
            except Exception:
                logging.getLogger(__name__).warning("Skill bundle upload parse failed")

        self._append_evolution_action_log(
            action_name="upload_skill_bundle",
            actor=payload.uploaded_by,
            detail="skill bundle uploaded",
            payload={
                "bundle_id": record.bundle_id,
                "team_id": record.team_id,
                "skill_id": record.skill_id,
                "version": record.version,
            },
        )

        return SkillBundleUploadResponse(bundle=record, detail="skill bundle uploaded")

    def download_skill_bundle(self, skill_id: str, version: str | None = None) -> SkillBundleRecord | None:
        candidates = [item for item in self.skill_bundles.values() if item.skill_id == skill_id]
        if version:
            candidates = [item for item in candidates if item.version == version]
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: item.created_at, reverse=True)[0]

    def generate_team_skill_sync_rules(self, team_id: str) -> TeamSkillSyncRuleResponse:
        bundle_ids = [
            item.bundle_id
            for item in self.skill_bundles.values()
            if item.team_id == team_id
        ]
        skill_ids = sorted(
            {
                item.skill_id
                for item in self.skill_bundles.values()
                if item.team_id == team_id
            }
        )
        rule = TeamSkillSyncRuleRecord(
            rule_set_id=self._next_id("ruleset"),
            team_id=team_id,
            based_on_bundle_ids=sorted(bundle_ids),
            synced_skill_ids=skill_ids,
            generated_at=datetime.now(UTC),
        )
        self.team_skill_sync_rules[rule.rule_set_id] = rule
        self._append_evolution_action_log(
            action_name="generate_team_skill_sync_rules",
            detail="sync rule generated",
            payload={
                "team_id": team_id,
                "rule_set_id": rule.rule_set_id,
                "skill_count": len(rule.synced_skill_ids),
            },
        )
        return TeamSkillSyncRuleResponse(rule=rule, detail="sync rule generated")

    def sync_team_skills(
        self,
        team_id: str,
        rule_set_id: str,
        payload: TeamSkillSyncApplyRequest,
    ) -> TeamSkillSyncApplyResponse:
        rule = self.team_skill_sync_rules.get(rule_set_id)
        if not rule or rule.team_id != team_id:
            raise ValueError("Rule set not found for team")

        detail = "dry run only" if payload.dry_run else "team skills synchronized"
        response = TeamSkillSyncApplyResponse(
            team_id=team_id,
            rule_set_id=rule_set_id,
            dry_run=payload.dry_run,
            synced_skill_ids=rule.synced_skill_ids,
            detail=detail,
        )
        self._append_evolution_action_log(
            action_name="sync_team_skills",
            detail=detail,
            payload={
                "team_id": team_id,
                "rule_set_id": rule_set_id,
                "dry_run": payload.dry_run,
                "synced_skill_count": len(rule.synced_skill_ids),
            },
        )
        return response

    def ingest_gateway_knowledge(self, payload: GatewayKnowledgeIngestRequest) -> GatewayKnowledgeIngestResponse:
        transformed = PassiveRagIngestRequest(
            min_quality_score=payload.min_quality_score,
            created_by=payload.created_by,
            items=[
                {
                    "source_type": "session" if item.source_type == "session" else "custom",
                    "source_id": item.source_id,
                    "title": item.title,
                    "content": item.content,
                    "project_id": item.team_id,
                    "tags": [
                        *item.tags,
                        "gateway-knowledge",
                        f"source:{item.source_type}",
                        *( [f"module:{item.module}"] if item.module else [] ),
                    ],
                    "quality_score": item.quality_score,
                    "metadata": {
                        **item.metadata,
                        "source_type": item.source_type,
                        "ingest_channel": "gateway",
                    },
                }
                for item in payload.items
            ],
        )
        result = self.ingest_passive_rag_items(transformed)
        response = GatewayKnowledgeIngestResponse(
            received=result.received,
            accepted=result.accepted,
            rejected=result.rejected,
            created_knowledge_ids=result.created_knowledge_ids,
            rejected_items=result.rejected_items,
        )
        self._append_evolution_action_log(
            action_name="ingest_gateway_knowledge",
            actor=payload.created_by,
            detail="gateway knowledge ingested",
            payload={
                "received": response.received,
                "accepted": response.accepted,
                "rejected": response.rejected,
            },
        )
        return response

    def summarize_rag_to_skill(self, payload: RagSummarizeToSkillRequest) -> RagSummarizeToSkillResponse:
        docs = self.list_knowledge(status="active")[: payload.limit]
        generated_update_ids: list[str] = []
        created_by = (payload.created_by or "rag-summarizer").strip() or "rag-summarizer"
        for doc in docs:
            doc_tags = set(doc.tags or [])
            if "gateway-knowledge" not in doc_tags and "passive-rag" not in doc_tags:
                continue

            update_id = self._next_id("skillupdate")
            now = datetime.now(UTC)
            suggestion_name = f"RAG总结:{doc.title[:24]}"
            record = SkillUpdateRecord(
                id=update_id,
                task_run_id="taskrun_rag_summarizer",
                skill_id=None,
                git_repo_id=None,
                proposed_skill_name=suggestion_name,
                proposed_system_prompt=(doc.content or "")[:2000],
                proposed_user_prompt_template="根据上下文完成任务，并遵守企业规范。",
                rationale=f"Generated from RAG knowledge {doc.id} by {created_by}",
                error_patterns=None,
                status="draft",
                export_path=None,
                git_commit_hash=None,
                created_at=now,
                updated_at=now,
            )
            if self._db_enabled:
                with self._connect() as conn, conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO backend_skill_updates (
                            skill_update_id, task_run_id, skill_id, git_repo_id, proposed_skill_name,
                            proposed_system_prompt, proposed_user_prompt_template,
                            rationale, error_patterns, status, export_path,
                            git_commit_hash, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            record.id,
                            record.task_run_id,
                            record.skill_id,
                            record.git_repo_id,
                            record.proposed_skill_name,
                            record.proposed_system_prompt,
                            record.proposed_user_prompt_template,
                            record.rationale,
                            record.error_patterns,
                            record.status,
                            record.export_path,
                            record.git_commit_hash,
                            record.created_at,
                            record.updated_at,
                        ),
                    )
            else:
                self.skill_updates[record.id] = record
            generated_update_ids.append(update_id)

        response = RagSummarizeToSkillResponse(
            scope=payload.scope,
            scanned=len(docs),
            generated_updates=len(generated_update_ids),
            generated_update_ids=generated_update_ids,
            detail="rag summary to skill finished",
        )
        self._append_evolution_action_log(
            action_name="summarize_rag_to_skill",
            actor=payload.created_by,
            detail=response.detail,
            payload={
                "scope": payload.scope,
                "scanned": response.scanned,
                "generated_updates": response.generated_updates,
            },
        )
        return response

    def generate_agent_workflow_from_rag(
        self,
        payload: GenerateAgentWorkflowRequest,
    ) -> GenerateAgentWorkflowResponse:
        docs = self.list_knowledge(status="active")[:20]
        source_knowledge_ids = [doc.id for doc in docs]
        updates = self.list_skill_updates(status="draft")[:20]
        source_skill_update_ids = [item.id for item in updates]

        now = datetime.now(UTC)
        workflow = AgentWorkflowRecord(
            workflow_id=self._next_id("workflow"),
            scope=payload.scope,
            title=f"AutoWorkflow {payload.scope} {now.strftime('%Y%m%d%H%M')}",
            source_knowledge_ids=source_knowledge_ids,
            source_skill_update_ids=source_skill_update_ids,
            steps=[
                "Collect context from RAG",
                "Load applicable team skills",
                "Execute MCP tools based on constraints",
                "Run validation and emit summary",
            ],
            status="draft",
            optimization_count=0,
            created_at=now,
            updated_at=now,
        )
        self.agent_workflows[workflow.workflow_id] = workflow
        self._append_evolution_action_log(
            action_name="generate_agent_workflow",
            actor=payload.created_by,
            detail="workflow generated",
            payload={
                "scope": payload.scope,
                "workflow_id": workflow.workflow_id,
            },
        )
        return GenerateAgentWorkflowResponse(workflow=workflow, detail="workflow generated")

    def optimize_agent_workflow(
        self,
        workflow_id: str,
        payload: OptimizeAgentWorkflowRequest,
    ) -> OptimizeAgentWorkflowResponse | None:
        workflow = self.agent_workflows.get(workflow_id)
        if workflow is None:
            return None

        now = datetime.now(UTC)
        optimized = workflow.model_copy(
            update={
                "status": "optimized",
                "optimization_count": workflow.optimization_count + 1,
                "steps": [
                    *workflow.steps,
                    f"Optimization pass with feedback_window={payload.feedback_window}",
                ],
                "updated_at": now,
            }
        )
        self.agent_workflows[workflow_id] = optimized
        self._append_evolution_action_log(
            action_name="optimize_agent_workflow",
            detail="workflow optimized",
            payload={
                "workflow_id": workflow_id,
                "feedback_window": payload.feedback_window,
                "optimization_count": optimized.optimization_count,
            },
        )
        return OptimizeAgentWorkflowResponse(workflow=optimized, detail="workflow optimized")

    def get_evolution_overview(self) -> EvolutionOverviewResponse:
        active_docs = self.list_knowledge(status="active")
        gateway_doc_total = sum(
            1
            for item in active_docs
            if "gateway-knowledge" in set(item.tags or [])
        )
        rag_skill_update_total = sum(
            1
            for item in self.list_skill_updates(status="draft")
            if item.task_run_id == "taskrun_rag_summarizer"
        )
        optimized_workflow_total = sum(
            1
            for item in self.agent_workflows.values()
            if item.status == "optimized"
        )
        return EvolutionOverviewResponse(
            skill_bundle_total=len(self.skill_bundles),
            team_rule_total=len(self.team_skill_sync_rules),
            gateway_knowledge_total=gateway_doc_total,
            rag_skill_update_total=rag_skill_update_total,
            agent_workflow_total=len(self.agent_workflows),
            optimized_workflow_total=optimized_workflow_total,
        )

    def list_evolution_action_logs(
        self,
        *,
        action_name: str | None = None,
        status: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EvolutionActionLogRecord]:
        records = sorted(
            self.evolution_action_logs.values(),
            key=lambda item: item.created_at,
            reverse=True,
        )
        if action_name:
            records = [item for item in records if item.action_name == action_name]
        if status:
            records = [item for item in records if item.status == status]
        if since is not None:
            records = [item for item in records if item.created_at >= since]
        if until is not None:
            records = [item for item in records if item.created_at <= until]
        return records[offset : offset + limit]

    def replay_last_success_action_chain(
        self,
        payload: ReplayEvolutionActionChainRequest,
    ) -> ReplayEvolutionActionChainResponse:
        candidates = sorted(
            [item for item in self.evolution_action_logs.values() if item.status == "success"],
            key=lambda item: item.created_at,
            reverse=True,
        )[: payload.limit]

        replayed_action_names: list[str] = []
        skipped_action_names: list[str] = []
        for item in reversed(candidates):
            action_name = item.action_name
            if self._execute_replay_action(action_name, item.payload or {}, dry_run=False):
                replayed_action_names.append(action_name)
            else:
                skipped_action_names.append(action_name)

        self._append_evolution_action_log(
            action_name="replay_last_success_action_chain",
            detail="replay chain finished",
            payload={
                "requested": payload.limit,
                "replayed": len(replayed_action_names),
                "skipped": len(skipped_action_names),
            },
        )

        return ReplayEvolutionActionChainResponse(
            requested=payload.limit,
            replayed=len(replayed_action_names),
            skipped=len(skipped_action_names),
            replayed_action_names=replayed_action_names,
            skipped_action_names=skipped_action_names,
            detail="replay completed",
        )

    def create_action_chain_template(
        self,
        payload: ActionChainTemplateCreateRequest,
    ) -> ActionChainTemplateRecord:
        now = datetime.now(UTC)
        action_names = [
            str(item).strip()
            for item in payload.action_names
            if str(item).strip()
        ]
        record = ActionChainTemplateRecord(
            template_id=self._next_id("action_template"),
            name=payload.name.strip(),
            action_names=action_names,
            created_by=(payload.created_by or "system").strip() or "system",
            created_at=now,
            updated_at=now,
        )
        self.action_chain_templates[record.template_id] = record
        self._append_evolution_action_log(
            action_name="create_action_chain_template",
            actor=record.created_by,
            detail="action chain template created",
            payload={
                "template_id": record.template_id,
                "name": record.name,
                "action_count": len(record.action_names),
            },
        )
        return record

    def list_action_chain_templates(self) -> list[ActionChainTemplateRecord]:
        return sorted(
            self.action_chain_templates.values(),
            key=lambda item: item.updated_at,
            reverse=True,
        )

    def run_action_chain_template(
        self,
        template_id: str,
        payload: ActionChainTemplateRunRequest,
    ) -> ActionChainTemplateRunResponse | None:
        template = self.action_chain_templates.get(template_id)
        if template is None:
            return None

        runtime_context = dict(payload.context or {})
        replayed_action_names: list[str] = []
        skipped_action_names: list[str] = []
        for action_name in template.action_names:
            if self._execute_replay_action(action_name, runtime_context, dry_run=payload.dry_run):
                replayed_action_names.append(action_name)
            else:
                skipped_action_names.append(action_name)

        result = ActionChainTemplateRunResponse(
            template_id=template.template_id,
            template_name=template.name,
            dry_run=payload.dry_run,
            replayed=len(replayed_action_names),
            skipped=len(skipped_action_names),
            replayed_action_names=replayed_action_names,
            skipped_action_names=skipped_action_names,
            detail="template run completed",
        )
        self._append_evolution_action_log(
            action_name="run_action_chain_template",
            actor=runtime_context.get("actor") if isinstance(runtime_context.get("actor"), str) else None,
            detail=result.detail,
            payload={
                "template_id": template.template_id,
                "template_name": template.name,
                "dry_run": payload.dry_run,
                "replayed": result.replayed,
                "skipped": result.skipped,
            },
        )
        return result

    def _execute_replay_action(self, action_name: str, payload: dict[str, Any], dry_run: bool) -> bool:
        pld = payload or {}
        try:
            if action_name == "upload_skill_bundle":
                team_id = str(pld.get("team_id") or "team_default")
                skill_id = str(pld.get("skill_id") or "")
                if not skill_id:
                    return False
                if dry_run:
                    return True
                self.upload_skill_bundle(
                    SkillBundleUploadRequest(
                        team_id=team_id,
                        skill_id=skill_id,
                        version=str(pld.get("version") or "v1"),
                        bundle={"source": "replay"},
                        tags=["replay"],
                        uploaded_by="replay-engine",
                    )
                )
                return True

            if action_name == "generate_team_skill_sync_rules":
                if dry_run:
                    return True
                self.generate_team_skill_sync_rules(str(pld.get("team_id") or "team_default"))
                return True

            if action_name == "sync_team_skills":
                team_id = str(pld.get("team_id") or "team_default")
                rule_set_id = str(pld.get("rule_set_id") or "")
                if not rule_set_id:
                    return False
                if dry_run:
                    return True
                self.sync_team_skills(team_id, rule_set_id, TeamSkillSyncApplyRequest(dry_run=True))
                return True

            if action_name == "ingest_gateway_knowledge":
                if dry_run:
                    return True
                self.ingest_gateway_knowledge(
                    GatewayKnowledgeIngestRequest(
                        created_by="replay-engine",
                        items=[
                            {
                                "source_type": "session",
                                "source_id": f"replay-{uuid4().hex[:8]}",
                                "title": "Replay effective knowledge",
                                "content": "Replay from action chain template.",
                                "team_id": str(pld.get("team_id") or "team_default"),
                                "tags": ["replay"],
                                "quality_score": 0.8,
                                "metadata": {"replay": True},
                            }
                        ],
                    )
                )
                return True

            if action_name == "summarize_rag_to_skill":
                if dry_run:
                    return True
                self.summarize_rag_to_skill(
                    RagSummarizeToSkillRequest(
                        scope=str(pld.get("scope") or "team"),
                        limit=10,
                        created_by="replay-engine",
                    )
                )
                return True

            if action_name == "generate_agent_workflow":
                if dry_run:
                    return True
                self.generate_agent_workflow_from_rag(
                    GenerateAgentWorkflowRequest(
                        scope=str(pld.get("scope") or "team"),
                        constraints={},
                        created_by="replay-engine",
                    )
                )
                return True

            if action_name == "optimize_agent_workflow":
                workflow_id = str(pld.get("workflow_id") or "")
                if not workflow_id:
                    return False
                if dry_run:
                    return True
                optimized = self.optimize_agent_workflow(
                    workflow_id,
                    OptimizeAgentWorkflowRequest(feedback_window=20),
                )
                return optimized is not None
        except Exception:
            return False

        return False

    def _append_evolution_action_log(
        self,
        *,
        action_name: str,
        status: str = "success",
        actor: str | None = None,
        detail: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> EvolutionActionLogRecord:
        record = EvolutionActionLogRecord(
            action_id=self._next_id("evolution_action"),
            action_name=action_name,
            status="failed" if status == "failed" else "success",
            actor=(actor or "system").strip() or "system",
            detail=detail,
            payload=payload or {},
            created_at=datetime.now(UTC),
        )
        self.evolution_action_logs[record.action_id] = record
        return record

    def get_hook_secret_status(self) -> HookSecretStatusResponse:
        self._ensure_schema_for_request()
        env_secret = (os.getenv("TEAM_AI_PLATFORM_HOOK_SECRET") or "").strip()
        if env_secret:
            return HookSecretStatusResponse(
                source="env",
                masked_secret=self._mask_secret(env_secret),
                updated_at=None,
            )

        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT secret_value, updated_at
                    FROM backend_runtime_secrets
                    WHERE secret_key = 'hook_secret'
                    """
                )
                row = cur.fetchone()
            if row and row[0]:
                return HookSecretStatusResponse(
                    source="db",
                    masked_secret=self._mask_secret(str(row[0])),
                    updated_at=row[1],
                )

        if self.hook_secret_override:
            return HookSecretStatusResponse(
                source="db",
                masked_secret=self._mask_secret(self.hook_secret_override),
                updated_at=self.hook_secret_updated_at,
            )

        return HookSecretStatusResponse(source="none", masked_secret=None, updated_at=None)

    def rotate_hook_secret(self, new_secret: str | None = None) -> HookSecretRotateResponse:
        self._ensure_schema_for_request()
        secret = (new_secret or "").strip() or f"hook_{uuid4().hex}{uuid4().hex[:8]}"
        now = datetime.now(UTC)

        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_runtime_secrets(secret_key, secret_value, updated_at)
                    VALUES ('hook_secret', %s, %s)
                    ON CONFLICT (secret_key)
                    DO UPDATE SET secret_value = EXCLUDED.secret_value,
                                  updated_at = EXCLUDED.updated_at
                    """,
                    (secret, now),
                )
        else:
            self.hook_secret_override = secret
            self.hook_secret_updated_at = now

        return HookSecretRotateResponse(
            source="db",
            new_secret=secret,
            masked_secret=self._mask_secret(secret),
            updated_at=now,
        )

    def get_effective_hook_secret(self) -> str:
        env_secret = (os.getenv("TEAM_AI_PLATFORM_HOOK_SECRET") or "").strip()
        if env_secret:
            return env_secret

        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT secret_value
                    FROM backend_runtime_secrets
                    WHERE secret_key = 'hook_secret'
                    """
                )
                row = cur.fetchone()
            return str(row[0]).strip() if row and row[0] else ""

        return (self.hook_secret_override or "").strip()

    @staticmethod
    def _mask_secret(secret: str) -> str:
        raw = (secret or "").strip()
        if len(raw) <= 8:
            return "*" * len(raw)
        return f"{raw[:4]}***{raw[-4:]}"

    def pull_git_repo_skills(self, repo_id: str) -> GitRepoPullSyncResponse | None:
        self._ensure_schema_for_request()
        repo = self.get_git_repo(repo_id)
        if repo is None:
            return None

        repo_dir = Path(repo.path).expanduser().resolve()
        if not repo_dir.exists():
            raise ValueError("Configured repository path does not exist")
        if not (repo_dir / ".git").exists():
            raise ValueError("Configured path is not a git repository")

        self._ensure_git_branch(repo_dir, repo.branch)

        pulled = False
        detail: str | None = None
        try:
            pull_proc = subprocess.run(
                ["git", "-C", str(repo_dir), "pull", "--ff-only", "origin", repo.branch],
                capture_output=True,
                text=True,
            )
            if pull_proc.returncode == 0:
                pulled = True
            else:
                detail = (pull_proc.stderr or pull_proc.stdout or "").strip() or None
        except Exception as exc:
            detail = str(exc)

        commit_sha: str | None = None
        try:
            rev_proc = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            commit_sha = (rev_proc.stdout or "").strip() or None
        except Exception:
            commit_sha = None

        skill_files = sorted(repo_dir.rglob("*.skill.json"))
        imported_skills = 0
        conflicts = 0
        conflict_update_ids: list[str] = []

        for file_path in skill_files:
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            skill_payload = self._extract_skill_payload(payload)
            if not skill_payload:
                continue

            ingest_result, ref_id = self._ingest_skill_from_repo_payload(
                repo=repo,
                skill_payload=skill_payload,
                source_file=file_path,
                commit_sha=commit_sha,
            )
            if ingest_result == "imported":
                imported_skills += 1
            elif ingest_result == "conflict":
                conflicts += 1
                if ref_id:
                    conflict_update_ids.append(ref_id)

        now = datetime.now(UTC)
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_git_repos
                    SET last_synced_at = %s,
                        updated_at = %s
                    WHERE git_repo_id = %s
                    """,
                    (now, now, repo.id),
                )
        else:
            self.git_repos[repo.id] = repo.model_copy(update={"last_synced_at": now, "updated_at": now})

        return GitRepoPullSyncResponse(
            repo_id=repo.id,
            branch=repo.branch,
            pulled=pulled,
            commit_sha=commit_sha,
            scanned_files=len(skill_files),
            imported_skills=imported_skills,
            conflicts=conflicts,
            conflict_update_ids=conflict_update_ids,
            detail=detail,
        )

    def _resolve_skill_ids_from_changed_files(self, changed_files: list[str]) -> list[str]:
        candidates = {Path(item).stem.lower() for item in changed_files if str(item).strip()}
        linked_ids: list[str] = []
        for skill in self.list_skills():
            slug = re.sub(r"[^a-z0-9]+", "-", skill.name.lower()).strip("-")
            if skill.id.lower() in candidates or slug in candidates:
                linked_ids.append(skill.id)
        return sorted(set(linked_ids))

    @staticmethod
    def _extract_skill_payload(document: Any) -> dict[str, Any] | None:
        if isinstance(document, dict):
            nested = document.get("skill")
            if isinstance(nested, dict):
                return nested
            if "name" in document and "system_prompt" in document:
                return document
        return None

    def _find_skill_by_name(self, name: str) -> SkillRecord | None:
        target = (name or "").strip().lower()
        if not target:
            return None
        for skill in self.list_skills():
            if skill.name.strip().lower() == target:
                return skill
        return None

    @staticmethod
    def _is_same_skill_content(existing: SkillRecord, proposed: dict[str, Any]) -> bool:
        proposed_tags = [str(item).strip() for item in (proposed.get("tags") or []) if str(item).strip()]
        return (
            existing.name.strip() == str(proposed.get("name", "")).strip()
            and existing.description.strip() == str(proposed.get("description", "")).strip()
            and existing.system_prompt.strip() == str(proposed.get("system_prompt", "")).strip()
            and existing.category.strip() == str(proposed.get("category", "general")).strip()
            and sorted(existing.tags) == sorted(proposed_tags)
        )

    def _attach_skill_update_context(self, update_id: str, skill_id: str, repo_id: str) -> None:
        self._ensure_schema_for_request()
        now = datetime.now(UTC)
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_skill_updates
                    SET skill_id = %s,
                        git_repo_id = %s,
                        updated_at = %s
                    WHERE skill_update_id = %s
                    """,
                    (skill_id, repo_id, now, update_id),
                )
            return

        update = self.skill_updates.get(update_id)
        if update:
            self.skill_updates[update_id] = update.model_copy(
                update={"skill_id": skill_id, "git_repo_id": repo_id, "updated_at": now}
            )

    def _ingest_skill_from_repo_payload(
        self,
        *,
        repo: GitRepoRecord,
        skill_payload: dict[str, Any],
        source_file: Path,
        commit_sha: str | None,
    ) -> tuple[str, str | None]:
        proposed_name = str(skill_payload.get("name") or "").strip()
        proposed_prompt = str(skill_payload.get("system_prompt") or "").strip()
        if not proposed_name or not proposed_prompt:
            return "noop", None

        existing = None
        proposed_id = str(skill_payload.get("id") or "").strip()
        if proposed_id:
            existing = self.get_skill(proposed_id)
        if existing is None:
            existing = self._find_skill_by_name(proposed_name)

        if existing is None:
            created = self.create_skill(
                SkillCreateRequest(
                    name=proposed_name,
                    description=str(skill_payload.get("description") or "").strip(),
                    system_prompt=proposed_prompt,
                    category=str(skill_payload.get("category") or "general").strip() or "general",
                    tags=[str(item).strip() for item in (skill_payload.get("tags") or []) if str(item).strip()],
                )
            )
            return "imported", created.id

        if self._is_same_skill_content(existing, skill_payload):
            return "noop", existing.id

        report = self.report_task_run(
            TaskRunReportRequest(
                tool_type="other",
                user_id="git-sync",
                task_title=f"Repo pull conflict: {proposed_name}",
                summary=(
                    f"Detected skill conflict while pulling from {repo.name}: "
                    f"{source_file.name} ({commit_sha or 'no-commit'})"
                ),
                lessons_learned="Manual review required before applying pulled skill update.",
                proposed_skill_name=proposed_name,
                proposed_system_prompt=proposed_prompt,
                proposed_user_prompt_template=str(skill_payload.get("proposed_user_prompt_template") or "").strip() or None,
            )
        )
        self._attach_skill_update_context(report.skill_update.id, existing.id, repo.id)
        return "conflict", report.skill_update.id

    @staticmethod
    def _ensure_git_branch(repo_dir: Path, branch: str) -> None:
        branch_name = (branch or "").strip()
        if not branch_name:
            return

        current = subprocess.run(
            ["git", "-C", str(repo_dir), "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
        )
        current_branch = (current.stdout or "").strip()
        if current_branch == branch_name:
            return

        verify = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "--verify", branch_name],
            capture_output=True,
            text=True,
        )
        if verify.returncode == 0:
            subprocess.run(
                ["git", "-C", str(repo_dir), "switch", branch_name],
                capture_output=True,
                text=True,
                check=True,
            )
            return

        subprocess.run(
            ["git", "-C", str(repo_dir), "switch", "-c", branch_name],
            capture_output=True,
            text=True,
            check=True,
        )

    def report_task_run(self, payload: TaskRunReportRequest) -> TaskRunReportResponse:
        self._ensure_schema_for_request()
        now = datetime.now(UTC)
        task_run_id = self._next_id("taskrun")
        skill_update_id = self._next_id("skillupdate")

        proposed_name = (payload.proposed_skill_name or "").strip() or None
        proposed_system_prompt = (payload.proposed_system_prompt or "").strip() or None
        proposed_user_prompt = (payload.proposed_user_prompt_template or "").strip() or None
        rationale = payload.summary.strip()
        if payload.lessons_learned:
            rationale = f"{rationale}\n\nLessons:\n{payload.lessons_learned.strip()}"

        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_task_runs (
                        task_run_id, tool_type, user_id, task_title, summary,
                        error_log, lessons_learned, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING task_run_id, tool_type, user_id, task_title, summary,
                              error_log, lessons_learned, created_at, updated_at
                    """,
                    (
                        task_run_id,
                        payload.tool_type,
                        payload.user_id,
                        payload.task_title,
                        payload.summary,
                        payload.error_log,
                        payload.lessons_learned,
                        now,
                        now,
                    ),
                )
                task_row = cur.fetchone()

                cur.execute(
                    """
                    INSERT INTO backend_skill_updates (
                        skill_update_id, task_run_id, skill_id, git_repo_id, proposed_skill_name,
                        proposed_system_prompt, proposed_user_prompt_template,
                        rationale, error_patterns, status, export_path,
                        git_commit_hash, created_at, updated_at
                    ) VALUES (%s, %s, NULL, NULL, %s, %s, %s, %s, %s, 'draft', NULL, NULL, %s, %s)
                    RETURNING skill_update_id, task_run_id, skill_id, git_repo_id, proposed_skill_name,
                              proposed_system_prompt, proposed_user_prompt_template,
                              rationale, error_patterns, status, export_path,
                              git_commit_hash, created_at, updated_at
                    """,
                    (
                        skill_update_id,
                        task_run_id,
                        proposed_name,
                        proposed_system_prompt,
                        proposed_user_prompt,
                        rationale,
                        payload.error_log,
                        now,
                        now,
                    ),
                )
                update_row = cur.fetchone()

            task_record = self._task_run_from_row(task_row)
            skill_update_record = self._skill_update_from_row(update_row)
            return TaskRunReportResponse(task_run=task_record, skill_update=skill_update_record)

        task_record = TaskRunRecord(
            id=task_run_id,
            tool_type=payload.tool_type,
            user_id=payload.user_id,
            task_title=payload.task_title,
            summary=payload.summary,
            error_log=payload.error_log,
            lessons_learned=payload.lessons_learned,
            created_at=now,
            updated_at=now,
        )
        update_record = SkillUpdateRecord(
            id=skill_update_id,
            task_run_id=task_run_id,
            skill_id=None,
            git_repo_id=None,
            proposed_skill_name=proposed_name,
            proposed_system_prompt=proposed_system_prompt,
            proposed_user_prompt_template=proposed_user_prompt,
            rationale=rationale,
            error_patterns=payload.error_log,
            status="draft",
            export_path=None,
            git_commit_hash=None,
            created_at=now,
            updated_at=now,
        )
        self.task_runs[task_run_id] = task_record
        self.skill_updates[skill_update_id] = update_record
        return TaskRunReportResponse(task_run=task_record, skill_update=update_record)

    def list_task_runs(self) -> list[TaskRunRecord]:
        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT task_run_id, tool_type, user_id, task_title, summary,
                           error_log, lessons_learned, created_at, updated_at
                    FROM backend_task_runs
                    ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()
            return [self._task_run_from_row(row) for row in rows]
        return sorted(self.task_runs.values(), key=lambda item: item.created_at, reverse=True)

    def list_skill_updates(self, status: str | None = None, skill_id: str | None = None) -> list[SkillUpdateRecord]:
        self._ensure_schema_for_request()
        if self._db_enabled:
            query = (
                "SELECT skill_update_id, task_run_id, skill_id, git_repo_id, proposed_skill_name, "
                "proposed_system_prompt, proposed_user_prompt_template, rationale, "
                "error_patterns, status, export_path, git_commit_hash, created_at, updated_at "
                "FROM backend_skill_updates WHERE 1=1"
            )
            params: list[Any] = []
            if status:
                query += " AND status = %s"
                params.append(status)
            if skill_id:
                query += " AND skill_id = %s"
                params.append(skill_id)
            query += " ORDER BY created_at DESC"

            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
            return [self._skill_update_from_row(row) for row in rows]

        updates = list(self.skill_updates.values())
        if status:
            updates = [item for item in updates if item.status == status]
        if skill_id:
            updates = [item for item in updates if item.skill_id == skill_id]
        return sorted(updates, key=lambda item: item.created_at, reverse=True)

    def apply_skill_update(self, update_id: str) -> SkillUpdateRecord | None:
        self._ensure_schema_for_request()
        update = self._get_skill_update(update_id)
        if update is None:
            return None

        now = datetime.now(UTC)
        target_skill_id = update.skill_id
        target_skill = self.get_skill(target_skill_id) if target_skill_id else None

        if target_skill is None:
            skill_name = (update.proposed_skill_name or "").strip() or "Learning Loop Skill"
            system_prompt = (
                (update.proposed_system_prompt or "").strip()
                or (update.rationale or "").strip()
                or "You are a helper that captures and reuses team learning outcomes."
            )
            rationale_summary = (update.rationale or "").strip() or "Learning loop generated skill update"
            target_skill = self.create_skill(
                SkillCreateRequest(
                    name=skill_name,
                    description=rationale_summary,
                    system_prompt=system_prompt,
                    category="general",
                    tags=["learning-loop"],
                )
            )
            target_skill_id = target_skill.id
        else:
            merged_prompt = (update.proposed_system_prompt or "").strip()
            merged_description = (update.rationale or "").strip()
            if merged_prompt or merged_description:
                if self._db_enabled:
                    prompt_value = merged_prompt or target_skill.system_prompt
                    with self._connect() as conn, conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE backend_skills
                            SET system_prompt = %s,
                                description = COALESCE(NULLIF(%s, ''), description),
                                updated_at = %s
                            WHERE skill_id = %s
                            """,
                            (prompt_value, merged_description, now, target_skill.id),
                        )
                    target_skill = self.get_skill(target_skill.id) or target_skill
                else:
                    update_data = {"system_prompt": merged_prompt or target_skill.system_prompt, "updated_at": now}
                    if merged_description:
                        update_data["description"] = merged_description
                    target_skill = target_skill.model_copy(update=update_data)
                    self.skills[target_skill.id] = target_skill
                self._upsert_skill_vector(target_skill)

        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_skill_updates
                    SET skill_id = %s,
                        status = 'applied',
                        updated_at = %s
                    WHERE skill_update_id = %s
                    RETURNING skill_update_id, task_run_id, skill_id, git_repo_id, proposed_skill_name,
                              proposed_system_prompt, proposed_user_prompt_template,
                              rationale, error_patterns, status, export_path,
                              git_commit_hash, created_at, updated_at
                    """,
                    (target_skill_id, now, update_id),
                )
                row = cur.fetchone()
            return self._skill_update_from_row(row) if row else None

        updated = update.model_copy(update={"skill_id": target_skill_id, "status": "applied", "updated_at": now})
        self.skill_updates[update_id] = updated
        return updated

    def sync_skill_update(self, update_id: str, payload: SkillUpdateSyncRequest) -> SkillUpdateRecord | None:
        self._ensure_schema_for_request()
        update = self._get_skill_update(update_id)
        if update is None:
            return None
        if update.status not in {"applied", "synced"}:
            raise ValueError("Skill update must be applied before sync")

        selected_repo: GitRepoRecord | None = None
        output_root = (payload.path or "").strip()
        auto_commit = payload.auto_commit

        if payload.mode == "git":
            if payload.repo_id:
                selected_repo = self.get_git_repo(payload.repo_id)
                if selected_repo is None:
                    raise ValueError("Configured git repository was not found")
            else:
                selected_repo = self.get_active_git_repo()

            if not output_root and selected_repo:
                output_root = selected_repo.path
            if not output_root and not selected_repo:
                raise ValueError("No active git repository configured; please bind one first")
            if auto_commit is None and selected_repo:
                auto_commit = selected_repo.auto_commit

        if not output_root:
            output_root = (os.getenv("TEAM_AI_PLATFORM_SKILL_SYNC_PATH") or "").strip()
        if not output_root:
            output_root = "/tmp/team_ai_skill_cache"
        if auto_commit is None:
            auto_commit = False

        output_dir = Path(output_root).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        if payload.mode == "git" and selected_repo and selected_repo.branch:
            try:
                self._ensure_git_branch(output_dir, selected_repo.branch)
            except FileNotFoundError as exc:
                raise ValueError("git command not found in runtime environment") from exc
            except subprocess.CalledProcessError as exc:
                stderr = (exc.stderr or "").strip()
                stdout = (exc.stdout or "").strip()
                detail = stderr or stdout or str(exc)
                raise ValueError(f"git branch switch failed: {detail}") from exc

        skill = self.get_skill(update.skill_id) if update.skill_id else None
        filename = f"{(skill.id if skill else update.id)}.skill.json"
        output_path = output_dir / filename

        now = datetime.now(UTC)
        bundle_update = update.model_copy(
            update={
                "status": "synced",
                "export_path": str(output_path),
                "git_repo_id": selected_repo.id if selected_repo else update.git_repo_id,
                "git_commit_hash": update.git_commit_hash,
                "updated_at": now,
            }
        )
        bundle = self._build_skill_bundle(bundle_update, skill)
        output_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

        git_commit_hash: str | None = None
        if payload.mode == "git":
            if not (output_dir / ".git").exists():
                raise ValueError("Git mode requires a repository path containing .git")
            rel_path = str(output_path.relative_to(output_dir))
            try:
                subprocess.run(
                    ["git", "-C", str(output_dir), "add", rel_path],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if auto_commit:
                    commit_msg = f"sync skill update {update.id}"
                    commit_proc = subprocess.run(
                        ["git", "-C", str(output_dir), "commit", "-m", commit_msg],
                        capture_output=True,
                        text=True,
                    )
                    commit_output = f"{commit_proc.stdout or ''}\n{commit_proc.stderr or ''}".lower()
                    if commit_proc.returncode != 0 and "nothing to commit" not in commit_output:
                        raise ValueError(f"git commit failed: {(commit_proc.stderr or commit_proc.stdout).strip()}")
                    rev_proc = subprocess.run(
                        ["git", "-C", str(output_dir), "rev-parse", "HEAD"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    git_commit_hash = (rev_proc.stdout or "").strip() or None
            except FileNotFoundError as exc:
                raise ValueError("git command not found in runtime environment") from exc
            except subprocess.CalledProcessError as exc:
                stderr = (exc.stderr or "").strip()
                stdout = (exc.stdout or "").strip()
                detail = stderr or stdout or str(exc)
                raise ValueError(f"git command failed: {detail}") from exc

        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_skill_updates
                    SET status = 'synced',
                        git_repo_id = COALESCE(%s, git_repo_id),
                        export_path = %s,
                        git_commit_hash = COALESCE(%s, git_commit_hash),
                        updated_at = %s
                    WHERE skill_update_id = %s
                    RETURNING skill_update_id, task_run_id, skill_id, git_repo_id, proposed_skill_name,
                              proposed_system_prompt, proposed_user_prompt_template,
                              rationale, error_patterns, status, export_path,
                              git_commit_hash, created_at, updated_at
                    """,
                    (selected_repo.id if selected_repo else None, str(output_path), git_commit_hash, now, update_id),
                )
                row = cur.fetchone()
                if selected_repo:
                    cur.execute(
                        """
                        UPDATE backend_git_repos
                        SET last_synced_at = %s,
                            updated_at = %s
                        WHERE git_repo_id = %s
                        """,
                        (now, now, selected_repo.id),
                    )
            return self._skill_update_from_row(row) if row else None

        updated = update.model_copy(
            update={
                "status": "synced",
                "git_repo_id": selected_repo.id if selected_repo else update.git_repo_id,
                "export_path": str(output_path),
                "git_commit_hash": git_commit_hash or update.git_commit_hash,
                "updated_at": now,
            }
        )
        self.skill_updates[update_id] = updated
        if selected_repo:
            repo_update = selected_repo.model_copy(update={"last_synced_at": now, "updated_at": now})
            self.git_repos[selected_repo.id] = repo_update
        return updated

    def _get_skill_update(self, update_id: str) -> SkillUpdateRecord | None:
        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT skill_update_id, task_run_id, skill_id, git_repo_id, proposed_skill_name,
                           proposed_system_prompt, proposed_user_prompt_template,
                           rationale, error_patterns, status, export_path,
                           git_commit_hash, created_at, updated_at
                    FROM backend_skill_updates
                    WHERE skill_update_id = %s
                    """,
                    (update_id,),
                )
                row = cur.fetchone()
            return self._skill_update_from_row(row) if row else None
        return self.skill_updates.get(update_id)

    @staticmethod
    def _build_skill_bundle(update: SkillUpdateRecord, skill: SkillRecord | None) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "synced_at": datetime.now(UTC).isoformat(),
            "skill_update": update.model_dump(mode="json"),
            "skill": skill.model_dump(mode="json") if skill else None,
        }

    def search_skills(self, query: str, limit: int = 10) -> list[SkillRecord]:
        started_at = perf_counter()
        normalized_query = (query or "").strip()
        if not normalized_query:
            records = self.list_skills()[:limit]
            self._skill_last_search_mode = "lexical"
            self._skill_last_search_result_count = len(records)
            self._skill_last_search_latency_ms = int((perf_counter() - started_at) * 1000)
            return records

        vector = self._embed_text(normalized_query)
        client = self._get_qdrant_client()
        if vector and client and qdrant_models is not None:
            try:
                self._ensure_qdrant_collection(client, len(vector))
                points = self._qdrant_search_points(
                    client,
                    collection_name=self._qdrant_collection_name(),
                    query_vector=vector,
                    limit=limit,
                    with_payload=False,
                )
                skill_ids = [str(point.id) for point in points if getattr(point, "id", None)]
                if skill_ids:
                    records: list[SkillRecord] = []
                    for skill_id in skill_ids:
                        record = self.get_skill(skill_id)
                        if record and record.status == "active":
                            records.append(record)
                    if records:
                        self._skill_last_search_mode = "vector"
                        self._skill_last_search_result_count = len(records)
                        self._skill_last_search_latency_ms = int((perf_counter() - started_at) * 1000)
                        return records
            except Exception:
                logging.getLogger(__name__).warning("Qdrant search failed, fallback to lexical skill search")

        records = self._lexical_skill_search(normalized_query, limit)
        self._skill_last_search_mode = "lexical"
        self._skill_last_search_result_count = len(records)
        self._skill_last_search_latency_ms = int((perf_counter() - started_at) * 1000)
        return records

    def probe_skill_embedding(self) -> bool:
        vector = self._embed_text("skill-search-health-check")
        return bool(vector)

    def get_skill_search_status(self) -> SkillSearchStatusResponse:
        now = datetime.now(UTC)
        qdrant_enabled = self._get_qdrant_client() is not None
        embedding_available = self._skill_embedding_available is True

        if self._skill_embedding_available is None:
            mode = "warming"
        elif qdrant_enabled and embedding_available:
            mode = "vector"
        else:
            mode = "lexical"

        next_retry_at = self._skill_embedding_retry_after
        if next_retry_at and next_retry_at <= now:
            next_retry_at = None

        return SkillSearchStatusResponse(
            mode=mode,
            qdrant_enabled=qdrant_enabled,
            qdrant_url=self._qdrant_url(),
            qdrant_collection=self._qdrant_collection_name(),
            embedding_model=self._skill_embedding_model(),
            embedding_available=embedding_available,
            last_search_mode=self._skill_last_search_mode,
            last_search_latency_ms=self._skill_last_search_latency_ms,
            last_search_result_count=self._skill_last_search_result_count,
            last_error=self._skill_embedding_last_error,
            next_retry_at=next_retry_at,
        )

    def _lexical_skill_search(self, query: str, limit: int) -> list[SkillRecord]:
        q = query.lower()
        scored: list[tuple[int, SkillRecord]] = []
        for record in self.list_skills():
            if record.status != "active":
                continue
            score = 0
            if q in record.name.lower():
                score += 5
            if q in record.description.lower():
                score += 3
            if q in record.category.lower():
                score += 2
            if any(q in tag.lower() for tag in record.tags):
                score += 2
            if score > 0:
                scored.append((score, record))

        scored.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
        return [record for _score, record in scored[:limit]]

    def _embed_text(self, text: str) -> list[float] | None:
        base_url = self._litellm_base_url()
        master_key = self._litellm_master_key()
        if not base_url or not master_key:
            self._skill_embedding_available = False
            self._skill_embedding_last_error = "LiteLLM base_url or master_key is not configured"
            return None

        now = datetime.now(UTC)
        if self._skill_embedding_retry_after and now < self._skill_embedding_retry_after:
            return None

        try:
            with httpx.Client(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
                response = client.post(
                    f"{base_url}/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {master_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._skill_embedding_model(),
                        "input": text,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                data = payload.get("data") or []
                if not data:
                    self._skill_embedding_available = False
                    self._skill_embedding_last_error = "Embedding response has empty data"
                    return None
                vector = data[0].get("embedding")
                if not isinstance(vector, list):
                    self._skill_embedding_available = False
                    self._skill_embedding_last_error = "Embedding response is missing vector data"
                    return None
                self._skill_embedding_available = True
                self._skill_embedding_last_error = None
                self._skill_embedding_retry_after = None
                return [float(v) for v in vector]
        except Exception as exc:
            self._skill_embedding_available = False
            self._skill_embedding_last_error = str(exc)[:240]
            self._skill_embedding_retry_after = now + timedelta(seconds=self._skill_embedding_retry_seconds())
            logging.getLogger(__name__).warning("Embedding request failed for skill indexing")
            return None

    def _upsert_skill_vector(self, record: SkillRecord) -> None:
        client = self._get_qdrant_client()
        if not client or qdrant_models is None:
            return

        vector_text = "\n".join(
            [
                record.name,
                record.description,
                record.system_prompt,
                record.category,
                " ".join(record.tags),
            ]
        ).strip()
        if not vector_text:
            return

        vector = self._embed_text(vector_text)
        if not vector:
            return

        try:
            self._ensure_qdrant_collection(client, len(vector))
            client.upsert(
                collection_name=self._qdrant_collection_name(),
                points=[
                    qdrant_models.PointStruct(
                        id=record.id,
                        vector=vector,
                        payload={
                            "skill_id": record.id,
                            "name": record.name,
                            "category": record.category,
                            "status": record.status,
                            "updated_at": record.updated_at.isoformat(),
                        },
                    )
                ],
                wait=False,
            )
        except Exception:
            logging.getLogger(__name__).warning("Qdrant upsert failed for skill_id=%s", record.id)

    def _delete_skill_vector(self, skill_id: str) -> None:
        client = self._get_qdrant_client()
        if not client or qdrant_models is None:
            return
        try:
            client.delete(
                collection_name=self._qdrant_collection_name(),
                points_selector=qdrant_models.PointIdsList(points=[skill_id]),
                wait=False,
            )
        except Exception:
            logging.getLogger(__name__).warning("Qdrant delete failed for skill_id=%s", skill_id)

    def _get_qdrant_client(self) -> Any | None:
        if self._qdrant_client is not None:
            return self._qdrant_client
        if self._qdrant_init_attempted:
            return None
        self._qdrant_init_attempted = True

        if QdrantClient is None:
            return None

        url = self._qdrant_url()
        if not url:
            return None

        try:
            self._qdrant_client = QdrantClient(url=url, timeout=5.0)
            self._qdrant_client.get_collections()
            return self._qdrant_client
        except Exception:
            logging.getLogger(__name__).warning("Qdrant is not available at %s", url)
            self._qdrant_client = None
            return None

    def _ensure_qdrant_collection(self, client: Any, dim: int, collection_name: str | None = None) -> None:
        if qdrant_models is None:
            return
        cname = collection_name or self._qdrant_collection_name()
        try:
            collection_info = client.get_collection(collection_name=cname)
            existing_size = collection_info.config.params.vectors.size
            if existing_size != dim:
                client.delete_collection(collection_name=cname)
                client.create_collection(
                    collection_name=cname,
                    vectors_config=qdrant_models.VectorParams(size=dim, distance=qdrant_models.Distance.COSINE),
                )
        except Exception:
            client.create_collection(
                collection_name=cname,
                vectors_config=qdrant_models.VectorParams(size=dim, distance=qdrant_models.Distance.COSINE),
            )

    @staticmethod
    def _qdrant_search_points(
        client: Any,
        *,
        collection_name: str,
        query_vector: list[float],
        limit: int,
        with_payload: bool,
    ) -> list[Any]:
        if hasattr(client, "search"):
            return client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=with_payload,
            )

        if hasattr(client, "query_points"):
            response = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                with_payload=with_payload,
            )
            points = getattr(response, "points", None)
            if points is not None:
                return list(points)
            if isinstance(response, dict):
                return list(response.get("points") or [])

        return []

    @staticmethod
    def _qdrant_url() -> str:
        return (os.getenv("TEAM_AI_PLATFORM_QDRANT_URL") or "http://localhost:6333").strip()

    @staticmethod
    def _qdrant_collection_name() -> str:
        return (os.getenv("TEAM_AI_PLATFORM_QDRANT_SKILLS_COLLECTION") or "team_ai_skills").strip()

    @staticmethod
    def _skill_embedding_model() -> str:
        return (os.getenv("TEAM_AI_PLATFORM_SKILL_EMBEDDING_MODEL") or "text-embedding-v3").strip()

    @staticmethod
    def _skill_embedding_retry_seconds() -> int:
        raw = (os.getenv("TEAM_AI_PLATFORM_SKILL_EMBEDDING_RETRY_SECONDS") or "120").strip()
        try:
            return max(5, int(raw))
        except Exception:
            return 120

    def create_session(self, payload: SessionCreateRequest) -> SessionRecord:
        now = datetime.now(UTC)
        session_id = self._next_id("session")
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_sessions (
                        session_id, user_id, project_id, title, summary,
                        memory_vector_id, status, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING session_id, user_id, project_id, title, summary,
                              memory_vector_id, status, created_at, updated_at
                    """,
                    (
                        session_id,
                        payload.user_id,
                        payload.project_id,
                        payload.title,
                        payload.summary,
                        None,
                        "active",
                        now,
                        now,
                    ),
                )
                row = cur.fetchone()
            return self._session_from_row(row)

        record = SessionRecord(
            id=session_id,
            user_id=payload.user_id,
            project_id=payload.project_id,
            title=payload.title,
            summary=payload.summary,
            memory_vector_id=None,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.sessions[session_id] = record
        return record

    def list_sessions(self) -> list[SessionRecord]:
        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT session_id, user_id, project_id, title, summary,
                           memory_vector_id, status, created_at, updated_at
                    FROM backend_sessions ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()
            return [self._session_from_row(row) for row in rows]
        return list(self.sessions.values())

    def get_session(self, session_id: str) -> SessionRecord | None:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT session_id, user_id, project_id, title, summary,
                           memory_vector_id, status, created_at, updated_at
                    FROM backend_sessions WHERE session_id = %s
                    """,
                    (session_id,),
                )
                row = cur.fetchone()
            return self._session_from_row(row) if row else None
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, payload: SessionUpdateRequest) -> SessionRecord | None:
        if self._db_enabled:
            record = self.get_session(session_id)
            if record is None:
                return None
            data = payload.model_dump(exclude_none=True)
            updated = record.model_copy(update=data | {"updated_at": datetime.now(UTC)})
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_sessions
                    SET title = %s,
                        summary = %s,
                        memory_vector_id = %s,
                        status = %s,
                        updated_at = %s
                    WHERE session_id = %s
                    """,
                    (
                        updated.title,
                        updated.summary,
                        updated.memory_vector_id,
                        updated.status,
                        updated.updated_at,
                        session_id,
                    ),
                )
            return updated

        record = self.sessions.get(session_id)
        if record is None:
            return None
        updated = record.model_copy(update=payload.model_dump(exclude_none=True) | {"updated_at": datetime.now(UTC)})
        self.sessions[session_id] = updated
        return updated

    def upsert_policy(self, payload: PolicyUpsertRequest) -> PolicyRecord:
        now = datetime.now(UTC)
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_policies (
                        policy_id, name, type, rules, status, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (name, type) DO UPDATE SET
                        rules = EXCLUDED.rules,
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at
                    RETURNING policy_id, name, type, rules, status, created_at, updated_at
                    """,
                    (
                        self._next_id("policy"),
                        payload.name,
                        payload.type,
                        Json(payload.rules),
                        payload.status,
                        now,
                        now,
                    ),
                )
                row = cur.fetchone()
            return self._policy_from_row(row)

        policy_id = self._find_policy_id(payload.name, payload.type) or self._next_id("policy")
        record = PolicyRecord(
            id=policy_id,
            name=payload.name,
            type=payload.type,
            rules=payload.rules,
            status=payload.status,
            created_at=now,
            updated_at=now,
        )
        self.policies[policy_id] = record
        return record

    def list_policies(self) -> list[PolicyRecord]:
        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT policy_id, name, type, rules, status, created_at, updated_at
                    FROM backend_policies ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()
            return [self._policy_from_row(row) for row in rows]
        return list(self.policies.values())

    def get_policy(self, policy_id: str) -> PolicyRecord | None:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT policy_id, name, type, rules, status, created_at, updated_at
                    FROM backend_policies WHERE policy_id = %s
                    """,
                    (policy_id,),
                )
                row = cur.fetchone()
            return self._policy_from_row(row) if row else None
        return self.policies.get(policy_id)

    def submit_approval(self, payload: ApprovalSubmitRequest) -> ApprovalRecord:
        now = datetime.now(UTC)
        approval_id = self._next_id("approval")
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_approvals (
                        approval_id, applicant_id, action, resource_id,
                        status, approver_id, reason, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING approval_id, applicant_id, action, resource_id,
                              status, approver_id, reason, created_at, updated_at
                    """,
                    (
                        approval_id,
                        payload.applicant_id,
                        payload.action,
                        payload.resource_id,
                        "pending",
                        None,
                        payload.reason,
                        now,
                        now,
                    ),
                )
                row = cur.fetchone()
            return self._approval_from_row(row)

        record = ApprovalRecord(
            id=approval_id,
            applicant_id=payload.applicant_id,
            action=payload.action,
            resource_id=payload.resource_id,
            status="pending",
            approver_id=None,
            reason=payload.reason,
            created_at=now,
            updated_at=now,
        )
        self.approvals[approval_id] = record
        return record

    def list_approvals(self) -> list[ApprovalRecord]:
        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT approval_id, applicant_id, action, resource_id,
                           status, approver_id, reason, created_at, updated_at
                    FROM backend_approvals ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()
            return [self._approval_from_row(row) for row in rows]
        return list(self.approvals.values())

    def get_approval(self, approval_id: str) -> ApprovalRecord | None:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT approval_id, applicant_id, action, resource_id,
                           status, approver_id, reason, created_at, updated_at
                    FROM backend_approvals WHERE approval_id = %s
                    """,
                    (approval_id,),
                )
                row = cur.fetchone()
            return self._approval_from_row(row) if row else None
        return self.approvals.get(approval_id)

    def approve_approval(self, approval_id: str, approver_id: str, reason: str | None = None) -> ApprovalRecord | None:
        """审批通过，返回更新后的 ApprovalRecord。"""
        self._ensure_schema_for_request()
        now = datetime.now(UTC)
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_approvals
                    SET status = 'approved', approver_id = %s, reason = %s, updated_at = %s
                    WHERE approval_id = %s AND status = 'pending'
                    RETURNING approval_id, applicant_id, action, resource_id,
                              status, approver_id, reason, created_at, updated_at
                    """,
                    (approver_id, reason, now, approval_id),
                )
                row = cur.fetchone()
            return self._approval_from_row(row) if row else None
        record = self.approvals.get(approval_id)
        if record and record.status == "pending":
            record.status = "approved"
            record.approver_id = approver_id
            record.reason = reason
            record.updated_at = now
        return record

    def reject_approval(self, approval_id: str, approver_id: str, reason: str | None = None) -> ApprovalRecord | None:
        """驳回审批，返回更新后的 ApprovalRecord。"""
        self._ensure_schema_for_request()
        now = datetime.now(UTC)
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_approvals
                    SET status = 'rejected', approver_id = %s, reason = %s, updated_at = %s
                    WHERE approval_id = %s AND status = 'pending'
                    RETURNING approval_id, applicant_id, action, resource_id,
                              status, approver_id, reason, created_at, updated_at
                    """,
                    (approver_id, reason, now, approval_id),
                )
                row = cur.fetchone()
            return self._approval_from_row(row) if row else None
        record = self.approvals.get(approval_id)
        if record and record.status == "pending":
            record.status = "rejected"
            record.approver_id = approver_id
            record.reason = reason
            record.updated_at = now
        return record

    # -----------------------------------------------------------------------
    # Knowledge CRUD  (Sprint 2: 持久化替代内存字典)
    # -----------------------------------------------------------------------

    @staticmethod
    def _knowledge_from_row(row: tuple[Any, ...]) -> "KnowledgeRecord":
        from .knowledge_schemas import KnowledgeRecord as _KR  # noqa: PLC0415
        tags = row[6] if isinstance(row[6], list) else []
        chunk_ids = row[9] if isinstance(row[9], list) else []
        return _KR(
            id=row[0],
            project_id=row[1],
            title=row[2],
            content=row[3],
            format=row[4],
            status=row[5],
            tags=tags,
            version=row[7],
            created_by=row[8] or "",
            qdrant_chunk_ids=chunk_ids,
            chunk_count=len(chunk_ids),
            created_at=row[10],
            updated_at=row[11],
        )

    def _knowledge_collection_name(self) -> str:
        return "team_ai_knowledge"

    def _embed_and_store_knowledge(self, knowledge_id: str, title: str, content: str) -> list[str]:
        """将知识文档分块 → embedding → 存入 Qdrant，返回 chunk_id 列表。失败时静默返回 []。"""
        client = self._get_qdrant_client()
        if client is None or qdrant_models is None:
            return []
        try:
            # 分块：512 字符，重叠 64 字符
            chunk_size, overlap = 512, 64
            full_text = f"# {title}\n\n{content}"
            chunks: list[str] = []
            start = 0
            while start < len(full_text):
                chunks.append(full_text[start : start + chunk_size])
                start += chunk_size - overlap
                if start + overlap >= len(full_text):
                    break

            # 逐个 chunk embedding
            chunk_ids: list[str] = []
            points: list[Any] = []
            for i, chunk in enumerate(chunks):
                vec = self._embed_text(chunk)
                if not vec:
                    continue
                cid_source = f"knowledge:{knowledge_id}:{i}"
                cid = str(uuid5(NAMESPACE_URL, cid_source))
                chunk_ids.append(cid)
                points.append(
                    qdrant_models.PointStruct(
                        id=cid,
                        vector=vec,
                        payload={
                            "knowledge_id": knowledge_id,
                            "chunk_index": i,
                            "text": chunk[:500],
                        },
                    )
                )

            if points:
                self._ensure_qdrant_collection(client, len(points[0].vector), self._knowledge_collection_name())
                client.upsert(collection_name=self._knowledge_collection_name(), points=points)
            return chunk_ids
        except Exception:
            logging.getLogger(__name__).warning("Knowledge embedding failed for %s", knowledge_id, exc_info=True)
            return []

    def _delete_knowledge_chunks(self, chunk_ids: list[str]) -> None:
        """从 Qdrant 删除指定的 chunk。"""
        if not chunk_ids:
            return
        client = self._get_qdrant_client()
        if client is None or qdrant_models is None:
            return
        try:
            client.delete(
                collection_name=self._knowledge_collection_name(),
                points_selector=qdrant_models.PointIdsList(points=chunk_ids),
            )
        except Exception:
            logging.getLogger(__name__).warning("Failed to delete knowledge chunks from Qdrant", exc_info=True)

    def create_knowledge(
        self,
        project_id: str,
        title: str,
        content: str,
        fmt: str,
        tags: list[str],
        created_by: str,
    ) -> "KnowledgeRecord":
        from .knowledge_schemas import KnowledgeRecord as _KR  # noqa: PLC0415
        self._ensure_schema_for_request()
        now = datetime.now(UTC)
        kid = self._next_id("kn")

        chunk_ids = self._embed_and_store_knowledge(kid, title, content)

        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_knowledge
                        (knowledge_id, project_id, title, content, format, status, tags,
                         version, created_by, qdrant_chunk_ids, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, 'active', %s, 1, %s, %s, %s, %s)
                    RETURNING knowledge_id, project_id, title, content, format, status, tags,
                              version, created_by, qdrant_chunk_ids, created_at, updated_at
                    """,
                    (kid, project_id, title, content, fmt, json.dumps(tags),
                     created_by, json.dumps(chunk_ids), now, now),
                )
                row = cur.fetchone()
            return self._knowledge_from_row(row)

        record = _KR(
            id=kid, project_id=project_id, title=title, content=content,
            format=fmt, status="active", tags=tags, version=1,
            created_by=created_by, qdrant_chunk_ids=chunk_ids,
            chunk_count=len(chunk_ids), created_at=now, updated_at=now,
        )
        return record

    def get_knowledge(self, knowledge_id: str) -> "KnowledgeRecord | None":
        self._ensure_schema_for_request()
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT knowledge_id, project_id, title, content, format, status, tags,
                           version, created_by, qdrant_chunk_ids, created_at, updated_at
                    FROM backend_knowledge WHERE knowledge_id = %s
                    """,
                    (knowledge_id,),
                )
                row = cur.fetchone()
            return self._knowledge_from_row(row) if row else None
        return None

    def list_knowledge(
        self, *, project_id: str | None = None, q: str | None = None, status: str | None = "active"
    ) -> list["KnowledgeRecord"]:
        self._ensure_schema_for_request()
        if self._db_enabled:
            query = (
                "SELECT knowledge_id, project_id, title, content, format, status, tags, "
                "version, created_by, qdrant_chunk_ids, created_at, updated_at "
                "FROM backend_knowledge WHERE 1=1"
            )
            params: list[Any] = []
            if project_id is not None:
                query += " AND project_id = %s"
                params.append(project_id)
            if status is not None:
                query += " AND status = %s"
                params.append(status)
            query += " ORDER BY created_at DESC"
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
            records = [self._knowledge_from_row(row) for row in rows]
            if q:
                ql = q.lower()
                records = [r for r in records if ql in r.title.lower() or ql in r.content.lower()]
            return records
        return []

    def update_knowledge(self, knowledge_id: str, updates: dict[str, Any]) -> "KnowledgeRecord | None":
        self._ensure_schema_for_request()
        now = datetime.now(UTC)
        record = self.get_knowledge(knowledge_id)
        if record is None:
            return None

        content_changed = "content" in updates or "title" in updates
        new_title = updates.get("title", record.title)
        new_content = updates.get("content", record.content)

        # 内容变更时重新向量化
        new_chunk_ids = record.qdrant_chunk_ids
        if content_changed:
            self._delete_knowledge_chunks(record.qdrant_chunk_ids)
            new_chunk_ids = self._embed_and_store_knowledge(knowledge_id, new_title, new_content)

        if self._db_enabled:
            fields: list[str] = []
            params: list[Any] = []
            for field in ("title", "content", "format", "tags", "status"):
                if field in updates:
                    fields.append(f"{field} = %s")
                    val = updates[field]
                    params.append(json.dumps(val) if isinstance(val, list) else val)
            if content_changed:
                fields.append("version = version + 1")
                fields.append("qdrant_chunk_ids = %s")
                params.append(json.dumps(new_chunk_ids))
            fields.append("updated_at = %s")
            params.append(now)
            params.append(knowledge_id)
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    f"UPDATE backend_knowledge SET {', '.join(fields)} WHERE knowledge_id = %s "  # noqa: S608
                    "RETURNING knowledge_id, project_id, title, content, format, status, tags, "
                    "version, created_by, qdrant_chunk_ids, created_at, updated_at",
                    tuple(params),
                )
                row = cur.fetchone()
            return self._knowledge_from_row(row) if row else None
        return None

    def delete_knowledge(self, knowledge_id: str) -> bool:
        self._ensure_schema_for_request()
        record = self.get_knowledge(knowledge_id)
        if record:
            self._delete_knowledge_chunks(record.qdrant_chunk_ids)
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("DELETE FROM backend_knowledge WHERE knowledge_id = %s", (knowledge_id,))
            return True
        return False

    def search_knowledge(self, query: str, limit: int = 5) -> list["KnowledgeRecord"]:
        """语义搜索知识库（向量检索，降级为关键词匹配）。"""
        if not query.strip():
            return self.list_knowledge()[:limit]
        vector = self._embed_text(query)
        client = self._get_qdrant_client()
        if vector and client and qdrant_models is not None:
            try:
                self._ensure_qdrant_collection(client, len(vector), self._knowledge_collection_name())
                points = self._qdrant_search_points(
                    client,
                    collection_name=self._knowledge_collection_name(),
                    query_vector=vector,
                    limit=limit * 3,  # 多取一些以去重
                    with_payload=True,
                )
                seen_ids: set[str] = set()
                records: list[Any] = []
                for point in points:
                    kid = (point.payload or {}).get("knowledge_id", "")
                    if kid and kid not in seen_ids:
                        seen_ids.add(kid)
                        rec = self.get_knowledge(kid)
                        if rec and rec.status == "active":
                            records.append(rec)
                            if len(records) >= limit:
                                break
                if records:
                    return records
            except Exception:
                logging.getLogger(__name__).warning("Qdrant knowledge search failed, fallback to keyword", exc_info=True)

        # 降级：关键词匹配
        ql = query.lower()
        all_docs = self.list_knowledge()
        return [r for r in all_docs if ql in r.title.lower() or ql in r.content.lower()][:limit]

    def list_providers(
        self,
        *,
        scope: str | None = None,
        app: str | None = None,
        enabled: bool | None = None,
    ) -> list[ProviderRecord]:
        self._ensure_schema_for_request()
        if self._db_enabled:
            query = (
                "SELECT provider_id, name, provider_type, base_url, preset_key, scope, apps, "
                "api_format, notes, enabled, metadata, api_key, created_at, updated_at "
                "FROM backend_providers WHERE 1=1"
            )
            params: list[Any] = []
            if scope is not None:
                query += " AND scope = %s"
                params.append(scope)
            if enabled is not None:
                query += " AND enabled = %s"
                params.append(enabled)
            if app is not None:
                query += " AND apps ? %s"
                params.append(app)
            query += " ORDER BY created_at DESC"
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
            return [self._provider_from_row(row) for row in rows]

        records = list(self.providers.values())
        if scope is not None:
            records = [record for record in records if record.scope == scope]
        if enabled is not None:
            records = [record for record in records if record.enabled == enabled]
        if app is not None:
            records = [record for record in records if app in record.apps]
        return records

    def create_provider(self, payload: ProviderCreateRequest) -> ProviderRecord:
        now = datetime.now(UTC)
        provider_id = self._next_id("provider")
        metadata = dict(payload.metadata or {})
        model_mappings = self._normalize_provider_model_mappings(
            payload.model_mappings if payload.model_mappings else metadata.get("model_mapping")
        )
        if model_mappings:
            metadata["model_mapping"] = model_mappings
        else:
            metadata.pop("model_mapping", None)
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_providers (
                        provider_id, name, provider_type, base_url, preset_key,
                        scope, apps, api_format, notes, enabled, metadata,
                        api_key, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING provider_id, name, provider_type, base_url, preset_key,
                              scope, apps, api_format, notes, enabled, metadata,
                              api_key, created_at, updated_at
                    """,
                    (
                        provider_id,
                        payload.name,
                        payload.provider_type,
                        payload.base_url,
                        payload.preset_key,
                        payload.scope,
                        Json(payload.apps),
                        payload.api_format,
                        payload.notes,
                        payload.enabled,
                        Json(metadata),
                        payload.api_key,
                        now,
                        now,
                    ),
                )
                row = cur.fetchone()
            result = self._provider_from_row(row)
            # Sync to litellm config after creating provider
            self._sync_providers_to_litellm_config()
            return result

        record = ProviderRecord(
            id=provider_id,
            name=payload.name,
            provider_type=payload.provider_type,
            base_url=payload.base_url,
            preset_key=payload.preset_key,
            scope=payload.scope,
            apps=payload.apps,
            api_format=payload.api_format,
            notes=payload.notes,
            enabled=payload.enabled,
            metadata=metadata,
            model_mappings=model_mappings,
            api_key_masked=self._mask_key(payload.api_key),
            created_at=now,
            updated_at=now,
        )
        self.providers[provider_id] = record
        self.provider_secrets[provider_id] = payload.api_key
        self._sync_providers_to_litellm_config()
        return record

    def get_provider(self, provider_id: str) -> ProviderRecord | None:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT provider_id, name, provider_type, base_url, preset_key,
                           scope, apps, api_format, notes, enabled, metadata,
                           api_key, created_at, updated_at
                    FROM backend_providers WHERE provider_id = %s
                    """,
                    (provider_id,),
                )
                row = cur.fetchone()
            return self._provider_from_row(row) if row else None
        return self.providers.get(provider_id)

    def update_provider(self, provider_id: str, payload: ProviderUpdateRequest) -> ProviderRecord | None:
        existing = self.get_provider(provider_id)
        if existing is None:
            return None

        if self._db_enabled:
            secret = self._get_provider_secret(provider_id)
            data = payload.model_dump(exclude_none=True)
            explicit_model_mappings = data.pop("model_mappings", None)
            metadata = dict(data.get("metadata") or existing.metadata or {})
            model_mappings = existing.model_mappings
            if explicit_model_mappings is not None:
                model_mappings = self._normalize_provider_model_mappings(explicit_model_mappings)
            if model_mappings:
                metadata["model_mapping"] = model_mappings
            else:
                metadata.pop("model_mapping", None)
            updated = existing.model_copy(
                update={k: v for k, v in data.items() if k not in {"api_key", "metadata"}}
                | {"metadata": metadata, "model_mappings": model_mappings, "updated_at": datetime.now(UTC)}
            )
            updated_secret = data.get("api_key", secret)
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_providers
                    SET name = %s,
                        provider_type = %s,
                        base_url = %s,
                        preset_key = %s,
                        scope = %s,
                        apps = %s,
                        api_format = %s,
                        notes = %s,
                        enabled = %s,
                        metadata = %s,
                        api_key = %s,
                        updated_at = %s
                    WHERE provider_id = %s
                    RETURNING provider_id, name, provider_type, base_url, preset_key,
                              scope, apps, api_format, notes, enabled, metadata,
                              api_key, created_at, updated_at
                    """,
                    (
                        updated.name,
                        updated.provider_type,
                        updated.base_url,
                        updated.preset_key,
                        updated.scope,
                        Json(updated.apps),
                        updated.api_format,
                        updated.notes,
                        updated.enabled,
                        Json(updated.metadata),
                        updated_secret,
                        updated.updated_at,
                        provider_id,
                    ),
                )
                row = cur.fetchone()
            result = self._provider_from_row(row)
            # Sync to litellm config after updating provider
            self._sync_providers_to_litellm_config()
            return result

        data = payload.model_dump(exclude_none=True)
        explicit_model_mappings = data.pop("model_mappings", None)
        metadata = dict(data.get("metadata") or existing.metadata or {})
        model_mappings = existing.model_mappings
        if explicit_model_mappings is not None:
            model_mappings = self._normalize_provider_model_mappings(explicit_model_mappings)
        if model_mappings:
            metadata["model_mapping"] = model_mappings
        else:
            metadata.pop("model_mapping", None)
        updated = existing.model_copy(
            update={k: v for k, v in data.items() if k not in {"api_key", "metadata"}}
            | {"metadata": metadata, "model_mappings": model_mappings, "updated_at": datetime.now(UTC)}
        )
        if "api_key" in data:
            self.provider_secrets[provider_id] = data["api_key"]
            updated = updated.model_copy(update={"api_key_masked": self._mask_key(data["api_key"])})
        self.providers[provider_id] = updated
        self._sync_providers_to_litellm_config()
        return updated

    def delete_provider(self, provider_id: str) -> bool:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("DELETE FROM backend_providers WHERE provider_id = %s", (provider_id,))
                deleted = cur.rowcount > 0
            # Sync to litellm config after deleting provider
            if deleted:
                self._sync_providers_to_litellm_config()
            return deleted
        existed = provider_id in self.providers
        self.providers.pop(provider_id, None)
        self.provider_secrets.pop(provider_id, None)
        if existed:
            self._sync_providers_to_litellm_config()
        return existed

    def sync_provider(self, provider_id: str, payload: ProviderSyncRequest) -> ProviderRecord | None:
        existing = self.get_provider(provider_id)
        if existing is None:
            return None

        metadata = dict(existing.metadata or {})
        model_mappings = self._normalize_provider_model_mappings(existing.model_mappings)
        if payload.sync_models:
            if model_mappings:
                endpoint = self._models_endpoint(existing.base_url)
                for mapping in model_mappings:
                    self.register_model(
                        ModelRegisterRequest(
                            provider=existing.provider_type,
                            provider_id=provider_id,
                            upstream_model=mapping["upstream_model"],
                            name=mapping["alias"],
                            endpoint=endpoint,
                            context_window=8192,
                            cost_tier="medium",
                            deployment_status="active",
                            labels={
                                "provider_name": existing.name,
                                "source": "provider_model_mapping",
                                **({"note": mapping["note"]} if mapping.get("note") else {}),
                            },
                        )
                    )
                metadata["model_mapping_synced_at"] = datetime.now(UTC).isoformat()
                metadata["model_mapping_source"] = "provider_mapping"
            api_key = self._get_provider_secret(provider_id)
            if api_key:
                discovered_model_ids = self._discover_provider_model_ids(existing, api_key)
                if discovered_model_ids:
                    metadata["model_ids"] = discovered_model_ids
                    metadata["model_source"] = "provider_discovery"
                    metadata["model_synced_at"] = datetime.now(UTC).isoformat()

        update_payload = ProviderUpdateRequest(
            scope="unified",
            apps=payload.target_apps or existing.apps,
            metadata=metadata,
        )
        return self.update_provider(provider_id, update_payload)

    def discover_provider_models(self, provider_id: str) -> ProviderModelDiscoveryResponse:
        provider = self.get_provider(provider_id)
        if provider is None:
            raise ValueError("Provider not found")
        api_key = self._get_provider_secret(provider_id)
        if not api_key:
            raise ValueError("Provider API key is missing")
        model_ids = self._discover_provider_model_ids(provider, api_key)
        endpoint = self._models_endpoint(provider.base_url)

        return ProviderModelDiscoveryResponse(
            provider_id=provider_id,
            endpoint=endpoint,
            models=sorted(set(model_ids)),
            fetched_at=datetime.now(UTC),
        )

    def discover_provider_models_live(
        self,
        payload: ProviderLiveModelDiscoveryRequest,
    ) -> ProviderLiveModelDiscoveryResponse:
        provider_type = payload.provider_type.strip()
        base_url = payload.base_url.strip()
        api_key = payload.api_key.strip()
        if not provider_type or not base_url or not api_key:
            raise ValueError("provider_type/base_url/api_key are required")

        model_ids = self._discover_provider_model_ids_raw(
            provider_type=provider_type,
            base_url=base_url,
            api_key=api_key,
        )
        return ProviderLiveModelDiscoveryResponse(
            endpoint=self._models_endpoint(base_url),
            models=sorted(set(model_ids)),
            fetched_at=datetime.now(UTC),
        )

    def probe_provider_endpoints(self, provider_id: str, payload: ProviderProbeRequest) -> ProviderProbeResponse:
        provider = self.get_provider(provider_id)
        if provider is None:
            raise ValueError("Provider not found")
        api_key = self._get_provider_secret(provider_id)
        if not api_key:
            raise ValueError("Provider API key is missing")

        timeout_ms = max(500, min(payload.timeout_ms, 30000))
        timeout_sec = timeout_ms / 1000.0
        requested = [endpoint.strip() for endpoint in payload.endpoints if endpoint.strip()]
        endpoints = requested or [provider.base_url]

        results: list[ProviderProbeResult] = []
        for base in endpoints:
            endpoint = self._models_endpoint(base)
            started = perf_counter()
            try:
                with httpx.Client(timeout=timeout_sec) as client:
                    response = client.get(endpoint, headers={"Authorization": f"Bearer {api_key}"})
                latency = int((perf_counter() - started) * 1000)
                ok = response.status_code < 500
                results.append(
                    ProviderProbeResult(
                        endpoint=base,
                        ok=ok,
                        status_code=response.status_code,
                        latency_ms=latency,
                        error=None if ok else f"HTTP {response.status_code}",
                    )
                )
            except Exception as exc:
                latency = int((perf_counter() - started) * 1000)
                results.append(
                    ProviderProbeResult(
                        endpoint=base,
                        ok=False,
                        status_code=None,
                        latency_ms=latency,
                        error=str(exc),
                    )
                )

        usable = [item for item in results if item.ok and item.latency_ms is not None]
        usable.sort(key=lambda item: item.latency_ms or 10**9)
        best_endpoint = usable[0].endpoint if usable else None
        response = ProviderProbeResponse(
            provider_id=provider_id,
            best_endpoint=best_endpoint,
            results=results,
            probed_at=datetime.now(UTC),
        )
        self._record_provider_probe(response)
        return response

    def list_provider_probe_logs(self, provider_id: str, limit: int = 20) -> list[ProviderProbeLogRecord]:
        if self.get_provider(provider_id) is None:
            raise ValueError("Provider not found")

        safe_limit = max(1, min(limit, 100))
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT log_id, provider_id, best_endpoint, results, probed_at
                    FROM backend_provider_probe_logs
                    WHERE provider_id = %s
                    ORDER BY probed_at DESC
                    LIMIT %s
                    """,
                    (provider_id, safe_limit),
                )
                rows = cur.fetchall()
            return [self._provider_probe_log_from_row(row) for row in rows]

        logs = self.provider_probe_logs.get(provider_id, [])
        return logs[:safe_limit]

    def batch_probe_providers(self, payload: ProviderBatchProbeRequest) -> ProviderBatchProbeResponse:
        target_ids = payload.provider_ids
        if not target_ids:
            target_ids = [record.id for record in self.list_providers(enabled=True)]

        items: list[ProviderBatchProbeItem] = []
        succeeded = 0
        for provider_id in target_ids:
            provider = self.get_provider(provider_id)
            if provider is None:
                items.append(
                    ProviderBatchProbeItem(
                        provider_id=provider_id,
                        provider_name="unknown",
                        best_endpoint=None,
                        applied=False,
                        results=[
                            ProviderProbeResult(
                                endpoint="",
                                ok=False,
                                status_code=None,
                                latency_ms=None,
                                error="Provider not found",
                            )
                        ],
                    )
                )
                continue

            probe = self.probe_provider_endpoints(
                provider_id,
                ProviderProbeRequest(endpoints=[provider.base_url], timeout_ms=payload.timeout_ms),
            )
            applied = False
            if payload.apply_best_endpoint and probe.best_endpoint and probe.best_endpoint != provider.base_url:
                updated = self.update_provider(provider_id, ProviderUpdateRequest(base_url=probe.best_endpoint))
                applied = updated is not None
            if probe.best_endpoint:
                succeeded += 1
            items.append(
                ProviderBatchProbeItem(
                    provider_id=provider_id,
                    provider_name=provider.name,
                    best_endpoint=probe.best_endpoint,
                    applied=applied,
                    results=probe.results,
                )
            )

        return ProviderBatchProbeResponse(
            items=items,
            total=len(items),
            succeeded=succeeded,
            probed_at=datetime.now(UTC),
        )

    def batch_update_providers(self, payload: ProviderBatchUpdateRequest) -> ProviderBatchUpdateResponse:
        if payload.enabled is None and payload.target_apps is None and not payload.force_unified:
            raise ValueError("No update fields provided")

        target_ids = payload.provider_ids
        if not target_ids:
            target_ids = [record.id for record in self.list_providers()]

        updated_ids: list[str] = []
        skipped_ids: list[str] = []
        for provider_id in target_ids:
            provider = self.get_provider(provider_id)
            if provider is None:
                skipped_ids.append(provider_id)
                continue

            update_payload = ProviderUpdateRequest(
                enabled=payload.enabled if payload.enabled is not None else None,
                apps=payload.target_apps if payload.target_apps is not None else None,
                scope="unified" if payload.force_unified else None,
            )
            updated = self.update_provider(provider_id, update_payload)
            if updated is None:
                skipped_ids.append(provider_id)
            else:
                updated_ids.append(provider_id)

        return ProviderBatchUpdateResponse(
            total=len(target_ids),
            updated=len(updated_ids),
            updated_ids=updated_ids,
            skipped_ids=skipped_ids,
        )

    def batch_delete_providers(self, payload: ProviderBatchDeleteRequest) -> ProviderBatchDeleteResponse:
        target_ids = payload.provider_ids
        if not target_ids:
            raise ValueError("No provider_ids provided")

        deleted_ids: list[str] = []
        skipped_ids: list[str] = []
        for provider_id in target_ids:
            if self.delete_provider(provider_id):
                deleted_ids.append(provider_id)
            else:
                skipped_ids.append(provider_id)

        return ProviderBatchDeleteResponse(
            total=len(target_ids),
            deleted=len(deleted_ids),
            deleted_ids=deleted_ids,
            skipped_ids=skipped_ids,
        )

    def _next_id(self, prefix: str) -> str:
        if self._db_enabled:
            return f"{prefix}_{uuid4().hex[:12]}"
        seq_map = {
            "model": self._model_seq,
            "key": self._key_seq,
            "skill": self._skill_seq,
            "session": self._session_seq,
            "taskrun": self._task_run_seq,
            "skillupdate": self._skill_update_seq,
            "gitrepo": self._git_repo_seq,
            "hookevent": self._hook_event_seq,
            "policy": self._policy_seq,
            "kn": self._knowledge_seq,
            "v2policy": self._v2_key_policy_seq,
            "approval": self._approval_seq,
            "provider": self._provider_seq,
            "provider_probe": self._provider_probe_seq,
            "bundle": self._bundle_seq,
            "ruleset": self._rule_set_seq,
            "workflow": self._workflow_seq,
            "evolution_action": self._evolution_action_seq,
            "action_template": self._action_template_seq,
        }
        return f"{prefix}_{next(seq_map[prefix])}"

    @staticmethod
    def _parse_json_like(raw: str) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            import json

            parsed = json.loads(raw)
        except Exception:
            return {"raw": raw}
        return parsed if isinstance(parsed, dict) else {"raw": parsed}

    def _find_policy_id(self, name: str, policy_type: str) -> str | None:
        for policy_id, record in self.policies.items():
            if record.name == name and record.type == policy_type:
                return policy_id
        return None

    @property
    def _db_enabled(self) -> bool:
        return bool(self.db_dsn)

    def _connect(self):
        if not self.db_dsn:
            raise RuntimeError("TEAM_AI_PLATFORM_DB_DSN is not configured")
        return psycopg2.connect(self.db_dsn)

    def _ensure_schema_once(self) -> None:
        if self._schema_ensured:
            return
        self._ensure_schema()
        self._schema_ensured = True

    def _ensure_schema_for_request(self) -> None:
        """Call at the start of any DB-accessing method to lazily init schema."""
        if not self._db_enabled or self._schema_ensured:
            return
        self._ensure_schema_once()

    def _ensure_schema(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_models (
                    model_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    provider_id TEXT,
                    upstream_model TEXT,
                    name TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    context_window INTEGER NOT NULL,
                    cost_tier TEXT NOT NULL,
                    availability TEXT NOT NULL DEFAULT 'active',
                    deployment_status TEXT NOT NULL DEFAULT 'active',
                    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                    labels JSONB NOT NULL DEFAULT '{}'::jsonb,
                    quota BIGINT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute("ALTER TABLE backend_models ADD COLUMN IF NOT EXISTS provider_id TEXT")
            cur.execute("ALTER TABLE backend_models ADD COLUMN IF NOT EXISTS upstream_model TEXT")
            cur.execute(
                "ALTER TABLE backend_models ADD COLUMN IF NOT EXISTS deployment_status TEXT NOT NULL DEFAULT 'active'"
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_keys (
                    key_id TEXT PRIMARY KEY,
                    key_hash TEXT NOT NULL UNIQUE,
                    label TEXT,
                    user_id TEXT,
                    project_id TEXT,
                    scope TEXT NOT NULL,
                    expire_at TIMESTAMPTZ,
                    quota BIGINT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            # Migration: add label column to existing tables
            cur.execute(
                "ALTER TABLE backend_keys ADD COLUMN IF NOT EXISTS label TEXT"
            )
            # Migration: add litellm_key_id column for LiteLLM bridge
            cur.execute(
                "ALTER TABLE backend_keys ADD COLUMN IF NOT EXISTS litellm_key_id TEXT"
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_backend_models_provider_availability
                ON backend_models(provider, availability)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_backend_keys_user_project_status
                ON backend_keys(user_id, project_id, status)
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_skills (
                    skill_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    system_prompt TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'general',
                    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                    version TEXT NOT NULL DEFAULT '1.0',
                    owner_id TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            # Migration: add new columns to existing skills table
            cur.execute("ALTER TABLE backend_skills ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT ''")
            cur.execute("ALTER TABLE backend_skills ADD COLUMN IF NOT EXISTS system_prompt TEXT NOT NULL DEFAULT ''")
            cur.execute("ALTER TABLE backend_skills ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'general'")
            cur.execute("ALTER TABLE backend_skills ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'::jsonb")
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_backend_skills_status_created
                ON backend_skills(status, created_at DESC)
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    project_id TEXT,
                    title TEXT,
                    summary TEXT,
                    memory_vector_id TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_task_runs (
                    task_run_id TEXT PRIMARY KEY,
                    tool_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    task_title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    error_log TEXT,
                    lessons_learned TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_git_repos (
                    git_repo_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    branch TEXT NOT NULL DEFAULT 'main',
                    auto_commit BOOLEAN NOT NULL DEFAULT FALSE,
                    is_active BOOLEAN NOT NULL DEFAULT FALSE,
                    last_synced_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_backend_git_repos_path
                ON backend_git_repos(path)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_backend_task_runs_created
                ON backend_task_runs(created_at DESC)
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_skill_updates (
                    skill_update_id TEXT PRIMARY KEY,
                    task_run_id TEXT NOT NULL REFERENCES backend_task_runs(task_run_id) ON DELETE CASCADE,
                    skill_id TEXT,
                    git_repo_id TEXT,
                    proposed_skill_name TEXT,
                    proposed_system_prompt TEXT,
                    proposed_user_prompt_template TEXT,
                    rationale TEXT NOT NULL,
                    error_patterns TEXT,
                    status TEXT NOT NULL DEFAULT 'draft',
                    export_path TEXT,
                    git_commit_hash TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_skill_hook_events (
                    hook_event_id TEXT PRIMARY KEY,
                    event_id TEXT,
                    idempotency_key TEXT NOT NULL,
                    repo_id TEXT,
                    repository TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    changed_files JSONB NOT NULL DEFAULT '[]'::jsonb,
                    linked_skill_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                    author TEXT,
                    event_time TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_runtime_secrets (
                    secret_key TEXT PRIMARY KEY,
                    secret_value TEXT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_backend_skill_hook_events_idempotency
                ON backend_skill_hook_events(idempotency_key)
                """
            )
            cur.execute(
                "ALTER TABLE backend_skill_updates ADD COLUMN IF NOT EXISTS git_repo_id TEXT"
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_backend_skill_updates_status_created
                ON backend_skill_updates(status, created_at DESC)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_backend_sessions_user_project_created
                ON backend_sessions(user_id, project_id, created_at DESC)
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_policies (
                    policy_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    rules JSONB NOT NULL DEFAULT '{}'::jsonb,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(name, type)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_approvals (
                    approval_id TEXT PRIMARY KEY,
                    applicant_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    approver_id TEXT,
                    reason TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_backend_approvals_status_created
                ON backend_approvals(status, created_at DESC)
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_providers (
                    provider_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    provider_type TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    preset_key TEXT,
                    scope TEXT NOT NULL DEFAULT 'app',
                    apps JSONB NOT NULL DEFAULT '[]'::jsonb,
                    api_format TEXT NOT NULL DEFAULT 'openai',
                    notes TEXT,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    api_key TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_backend_providers_scope_enabled_created
                ON backend_providers(scope, enabled, created_at DESC)
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_provider_probe_logs (
                    log_id TEXT PRIMARY KEY,
                    provider_id TEXT NOT NULL,
                    best_endpoint TEXT,
                    results JSONB NOT NULL DEFAULT '[]'::jsonb,
                    probed_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_backend_provider_probe_logs_provider_time
                ON backend_provider_probe_logs(provider_id, probed_at DESC)
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS cp_virtual_keys (
                    key_id TEXT PRIMARY KEY,
                    key_hash TEXT NOT NULL UNIQUE,
                    team_id TEXT NOT NULL,
                    alias TEXT,
                    owner_type TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    expires_at TIMESTAMPTZ,
                    rotated_from TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    revoked_at TIMESTAMPTZ
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_cp_virtual_keys_team_owner_status
                ON cp_virtual_keys(team_id, owner_type, owner_id, status)
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS cp_key_policies (
                    policy_id TEXT PRIMARY KEY,
                    key_id TEXT NOT NULL UNIQUE REFERENCES cp_virtual_keys(key_id) ON DELETE CASCADE,
                    allowed_models JSONB NOT NULL DEFAULT '[]'::jsonb,
                    denied_models JSONB NOT NULL DEFAULT '[]'::jsonb,
                    quota_tokens_day BIGINT,
                    quota_tokens_month BIGINT,
                    rate_limit_rpm INTEGER,
                    burst_limit INTEGER,
                    emergency_block BOOLEAN NOT NULL DEFAULT FALSE,
                    effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
                    effective_to TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            # Sprint 2: 知识库持久化表（替代内存字典）
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_knowledge (
                    knowledge_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    format TEXT NOT NULL DEFAULT 'markdown',
                    status TEXT NOT NULL DEFAULT 'active',
                    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                    version INTEGER NOT NULL DEFAULT 1,
                    created_by TEXT,
                    qdrant_chunk_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_backend_knowledge_project_status
                ON backend_knowledge(project_id, status, created_at DESC)
                """
            )

    @staticmethod
    def _model_from_row(row: tuple[Any, ...]) -> ModelRecord:
        tags = row[10] if isinstance(row[10], list) else []
        labels = row[11] if isinstance(row[11], dict) else {}
        return ModelRecord(
            id=row[0],
            provider=row[1],
            provider_id=row[2],
            upstream_model=row[3],
            name=row[4],
            endpoint=row[5],
            context_window=row[6],
            cost_tier=row[7],
            availability=row[8],
            deployment_status=row[9],
            tags=tags,
            labels=labels,
            quota=row[12],
            created_at=row[13],
            updated_at=row[14],
        )

    @staticmethod
    def _key_from_row(row: tuple[Any, ...]) -> KeyRecord:
        return KeyRecord(
            id=row[0],
            key_hash=row[1],
            label=row[2],
            user_id=row[3],
            project_id=row[4],
            scope=row[5],
            expire_at=row[6],
            quota=row[7],
            status=row[8],
            created_at=row[9],
            updated_at=row[10],
            litellm_key_id=row[11] if len(row) > 11 else None,
        )

    @staticmethod
    def _skill_from_row(row: tuple[Any, ...]) -> SkillRecord:
        tags = row[5] if isinstance(row[5], list) else []
        return SkillRecord(
            id=row[0],
            name=row[1],
            description=row[2] or "",
            system_prompt=row[3] or "",
            category=row[4] or "general",
            tags=tags,
            status=row[6],
            created_at=row[7],
            updated_at=row[8],
        )

    @staticmethod
    def _session_from_row(row: tuple[Any, ...]) -> SessionRecord:
        return SessionRecord(
            id=row[0],
            user_id=row[1],
            project_id=row[2],
            title=row[3],
            summary=row[4],
            memory_vector_id=row[5],
            status=row[6],
            created_at=row[7],
            updated_at=row[8],
        )

    @staticmethod
    def _task_run_from_row(row: tuple[Any, ...]) -> TaskRunRecord:
        return TaskRunRecord(
            id=row[0],
            tool_type=row[1],
            user_id=row[2],
            task_title=row[3],
            summary=row[4],
            error_log=row[5],
            lessons_learned=row[6],
            created_at=row[7],
            updated_at=row[8],
        )

    @staticmethod
    def _skill_update_from_row(row: tuple[Any, ...]) -> SkillUpdateRecord:
        return SkillUpdateRecord(
            id=row[0],
            task_run_id=row[1],
            skill_id=row[2],
            git_repo_id=row[3],
            proposed_skill_name=row[4],
            proposed_system_prompt=row[5],
            proposed_user_prompt_template=row[6],
            rationale=row[7],
            error_patterns=row[8],
            status=row[9],
            export_path=row[10],
            git_commit_hash=row[11],
            created_at=row[12],
            updated_at=row[13],
        )

    @staticmethod
    def _git_repo_from_row(row: tuple[Any, ...]) -> GitRepoRecord:
        return GitRepoRecord(
            id=row[0],
            name=row[1],
            path=row[2],
            branch=row[3],
            auto_commit=row[4],
            is_active=row[5],
            last_synced_at=row[6],
            created_at=row[7],
            updated_at=row[8],
        )

    @staticmethod
    def _hook_event_from_row(row: tuple[Any, ...]) -> SkillHookEventRecord:
        changed_files = row[7] if isinstance(row[7], list) else []
        linked_skill_ids = row[8] if isinstance(row[8], list) else []
        return SkillHookEventRecord(
            hook_event_id=row[0],
            event_id=row[1],
            idempotency_key=row[2],
            repo_id=row[3],
            repository=row[4],
            branch=row[5],
            commit_sha=row[6],
            changed_files=[str(item) for item in changed_files],
            linked_skill_ids=[str(item) for item in linked_skill_ids],
            author=row[9],
            event_time=row[10],
            created_at=row[11],
        )

    @staticmethod
    def _policy_from_row(row: tuple[Any, ...]) -> PolicyRecord:
        rules = row[3] if isinstance(row[3], dict) else {}
        return PolicyRecord(
            id=row[0],
            name=row[1],
            type=row[2],
            rules=rules,
            status=row[4],
            created_at=row[5],
            updated_at=row[6],
        )

    @staticmethod
    def _approval_from_row(row: tuple[Any, ...]) -> ApprovalRecord:
        return ApprovalRecord(
            id=row[0],
            applicant_id=row[1],
            action=row[2],
            resource_id=row[3],
            status=row[4],
            approver_id=row[5],
            reason=row[6],
            created_at=row[7],
            updated_at=row[8],
        )

    @staticmethod
    def _v2_virtual_key_from_row(row: tuple[Any, ...]) -> V2VirtualKeyRecord:
        return V2VirtualKeyRecord(
            key_id=row[0],
            team_id=row[1],
            alias=row[2],
            owner_type=row[3],
            owner_id=row[4],
            status=row[5],
            expires_at=row[6],
            rotated_from=row[7],
            created_at=row[8],
            updated_at=row[9],
            revoked_at=row[10],
        )

    @staticmethod
    def _v2_key_policy_from_row(row: tuple[Any, ...]) -> V2KeyPolicyRecord:
        allowed_models = row[2] if isinstance(row[2], list) else []
        denied_models = row[3] if isinstance(row[3], list) else []
        return V2KeyPolicyRecord(
            policy_id=row[0],
            key_id=row[1],
            allowed_models=allowed_models,
            denied_models=denied_models,
            quota_tokens_day=row[4],
            quota_tokens_month=row[5],
            rate_limit_rpm=row[6],
            burst_limit=row[7],
            emergency_block=row[8],
            effective_from=row[9],
            effective_to=row[10],
            created_at=row[11],
            updated_at=row[12],
        )

    def _get_provider_secret(self, provider_id: str) -> str | None:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("SELECT api_key FROM backend_providers WHERE provider_id = %s", (provider_id,))
                row = cur.fetchone()
            return row[0] if row else None
        return self.provider_secrets.get(provider_id)

    @staticmethod
    def _mask_key(raw: str) -> str:
        if len(raw) <= 8:
            return "*" * len(raw)
        return f"{raw[:4]}...{raw[-4:]}"

    @staticmethod
    def _models_endpoint(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        # Guard against accidental double suffixes like `/v1/v1`.
        normalized = re.sub(r"(?:/v1)+$", "/v1", normalized, flags=re.IGNORECASE)
        if normalized.endswith("/v1"):
            return f"{normalized}/models"
        return f"{normalized}/v1/models"

    @staticmethod
    def _normalize_provider_model_mappings(raw_mappings: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_mappings, list):
            return []
        normalized: list[dict[str, Any]] = []
        for item in raw_mappings:
            if not isinstance(item, dict):
                continue
            alias = str(item.get("alias", "")).strip()
            upstream_model = str(item.get("upstream_model", "")).strip()
            if not alias or not upstream_model:
                continue
            entry: dict[str, Any] = {
                "alias": alias,
                "upstream_model": upstream_model,
            }
            note = item.get("note")
            if isinstance(note, str) and note.strip():
                entry["note"] = note.strip()
            normalized.append(entry)
        return normalized

    def _provider_from_row(self, row: tuple[Any, ...]) -> ProviderRecord:
        apps = row[6] if isinstance(row[6], list) else []
        metadata = row[10] if isinstance(row[10], dict) else {}
        api_key = row[11] if isinstance(row[11], str) else ""
        model_mappings = self._normalize_provider_model_mappings(metadata.get("model_mapping"))
        return ProviderRecord(
            id=row[0],
            name=row[1],
            provider_type=row[2],
            base_url=row[3],
            preset_key=row[4],
            scope=row[5],
            apps=apps,
            api_format=row[7],
            notes=row[8],
            enabled=row[9],
            metadata=metadata,
            model_mappings=model_mappings,
            api_key_masked=self._mask_key(api_key) if api_key else None,
            created_at=row[12],
            updated_at=row[13],
        )

    def _record_provider_probe(self, payload: ProviderProbeResponse) -> None:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_provider_probe_logs (
                        log_id, provider_id, best_endpoint, results, probed_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        self._next_id("provider_probe"),
                        payload.provider_id,
                        payload.best_endpoint,
                        Json([item.model_dump() for item in payload.results]),
                        payload.probed_at,
                    ),
                )
            return

        log = ProviderProbeLogRecord(
            id=self._next_id("provider_probe"),
            provider_id=payload.provider_id,
            best_endpoint=payload.best_endpoint,
            results=payload.results,
            probed_at=payload.probed_at,
        )
        logs = self.provider_probe_logs.setdefault(payload.provider_id, [])
        logs.insert(0, log)
        if len(logs) > 100:
            del logs[100:]

    @staticmethod
    def _probe_result_from_dict(data: dict[str, Any]) -> ProviderProbeResult:
        return ProviderProbeResult(
            endpoint=str(data.get("endpoint", "")),
            ok=bool(data.get("ok", False)),
            status_code=data.get("status_code"),
            latency_ms=data.get("latency_ms"),
            error=data.get("error"),
        )

    def _provider_probe_log_from_row(self, row: tuple[Any, ...]) -> ProviderProbeLogRecord:
        raw_results = row[3] if isinstance(row[3], list) else []
        results = [
            self._probe_result_from_dict(item)
            for item in raw_results
            if isinstance(item, dict)
        ]
        return ProviderProbeLogRecord(
            id=row[0],
            provider_id=row[1],
            best_endpoint=row[2],
            results=results,
            probed_at=row[4],
        )

    def preview_litellm_runtime_config(self) -> RuntimeConfigPreviewResponse:
        config, _env_vars, provider_count, observability_backend = self._build_litellm_runtime_artifacts()
        model_count = len(config.get("model_list", []))
        return RuntimeConfigPreviewResponse(
            provider_count=provider_count,
            model_count=model_count,
            observability_backend=observability_backend,
            config=config,
        )

    def apply_litellm_runtime_config(self, output_dir: str | None = None) -> RuntimeConfigApplyResponse:
        config, env_vars, provider_count, observability_backend = self._build_litellm_runtime_artifacts()
        config_path, env_path = self._resolve_litellm_output_paths(output_dir)

        # Write config without model_list: models are now fully managed via the
        # LiteLLM DB API (/model/new + /model/delete) with STORE_MODEL_IN_DB=True.
        config_for_yaml = {k: v for k, v in config.items() if k != "model_list"}
        with config_path.open("w", encoding="utf-8") as config_file:
            yaml.safe_dump(config_for_yaml, config_file, default_flow_style=False, sort_keys=False)

        with env_path.open("w", encoding="utf-8") as env_file:
            env_file.write("# LiteLLM provider API keys - auto-generated by backend\n")
            env_file.write("# This file is generated by backend/app/store.py from control-plane state\n")
            for key, value in sorted(env_vars.items()):
                env_file.write(f"{key}={value}\n")

        return RuntimeConfigApplyResponse(
            provider_count=provider_count,
            model_count=len(config.get("model_list", [])),
            observability_backend=observability_backend,
            config_path=str(config_path),
            env_path=str(env_path),
            written_at=datetime.now(UTC),
        )

    def _sync_providers_to_litellm_config(self) -> None:
        """Sync enabled providers from control-plane state to litellm config files."""
        try:
            self.apply_litellm_runtime_config()
        except Exception as exc:
            logging.getLogger(__name__).error("Failed to sync providers to litellm config: %s", exc)
            return

        try:
            runtime_sync = self.sync_litellm_gateway_runtime()
            if not runtime_sync.ok:
                logging.getLogger(__name__).warning(
                    "LiteLLM gateway hot sync skipped/failed: %s",
                    runtime_sync.detail or "unknown error",
                )
        except Exception as exc:
            logging.getLogger(__name__).warning("Failed to hot sync LiteLLM gateway: %s", exc)

    def sync_litellm_gateway_runtime(self) -> ProviderGatewaySyncResponse:  # noqa: C901
        """Diff-sync desired models with the LiteLLM gateway via DB API.

        Uses STORE_MODEL_IN_DB=True semantics:
        - GET  /model/info          → current DB-managed models (model_name → id)
        - POST /model/delete {id}   → remove models no longer desired
        - POST /model/new {...}     → add newly desired models

        Models that exist in both current and desired are left untouched.
        To force a full resync (e.g., after an API key rotation), delete all
        models from the LiteLLM admin UI or call /model/delete manually first.
        """
        config, env_vars, _provider_count, _observability_backend = self._build_litellm_runtime_artifacts()
        desired_models = self._build_litellm_hot_model_list(config.get("model_list", []), env_vars)
        synced_at = datetime.now(UTC)

        base_url = self._litellm_base_url()
        master_key = self._litellm_master_key()
        if not base_url or not master_key:
            return ProviderGatewaySyncResponse(
                ok=False,
                model_count=len(desired_models),
                endpoint=None,
                detail="LiteLLM admin endpoint or master key is not configured",
                synced_at=synced_at,
            )

        headers = {"Authorization": f"Bearer {master_key}", "Content-Type": "application/json"}
        timeout = httpx.Timeout(30.0, connect=5.0)
        errors: list[str] = []

        with httpx.Client(timeout=timeout) as client:
            # 1. Fetch current DB-managed models from the LiteLLM gateway.
            try:
                resp = client.get(f"{base_url}/model/info", headers=headers)
                if resp.status_code >= 500:
                    # LiteLLM not yet fully loaded (no models registered). Treat as empty.
                    current_models: dict[str, str] = {}
                else:
                    resp.raise_for_status()
                    current_models: dict[str, list[dict[str, Any]]] = {}
                    for model in resp.json().get("data", []):
                        if not isinstance(model, dict):
                            continue
                        model_name = model.get("model_name")
                        model_info = model.get("model_info")
                        if (
                            not isinstance(model_name, str)
                            or not model_name
                            or not isinstance(model_info, dict)
                            or not model_info.get("id")
                            or model_info.get("db_model") is not True
                        ):
                            continue
                        current_models.setdefault(model_name, []).append(
                            {
                                "id": str(model_info["id"]),
                                "litellm_params": model.get("litellm_params") or {},
                            }
                        )
            except Exception as exc:
                return ProviderGatewaySyncResponse(
                    ok=False,
                    model_count=len(desired_models),
                    endpoint=f"{base_url}/model/info",
                    detail=f"Failed to fetch current gateway model list: {exc}",
                    synced_at=synced_at,
                )

            desired_by_name = {m["model_name"]: m for m in desired_models}
            desired_names = set(desired_by_name)
            current_names = set(current_models)
            to_delete: list[tuple[str, str]] = []
            to_add_names: set[str] = set(desired_names - current_names)

            def _canonical(value: dict[str, Any]) -> str:
                # Stable normalization for drift detection between desired/current model params.
                return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

            def _collect_delete_ids(model_entries: list[dict[str, Any]]) -> list[str]:
                ids: list[str] = []
                seen: set[str] = set()
                for model_entry in model_entries:
                    candidate = str(model_entry.get("id", "")).strip()
                    if not candidate or candidate in seen:
                        continue
                    seen.add(candidate)
                    ids.append(candidate)
                return ids

            for model_name, model_entries in current_models.items():
                if model_name not in desired_names:
                    for delete_id in _collect_delete_ids(model_entries):
                        to_delete.append((model_name, delete_id))
                    continue

                desired_params = desired_by_name[model_name].get("litellm_params") or {}
                current_params = (model_entries[0].get("litellm_params") or {}) if model_entries else {}

                if _canonical(current_params) != _canonical(desired_params):
                    # Parameter drift (e.g. api_base / model mapping changed):
                    # purge all rows for this model_name and re-add with latest params.
                    for delete_id in _collect_delete_ids(model_entries):
                        to_delete.append((model_name, delete_id))
                    to_add_names.add(model_name)
                    continue

                # /model/info can duplicate one DB model across multiple workers.
                # Keep steady-state rows intact; only remove on explicit delete/drift.

            # 2. Remove models no longer in the desired list.
            for model_name, model_id in sorted(to_delete):
                try:
                    resp = client.post(
                        f"{base_url}/model/delete",
                        headers=headers,
                        json={"id": model_id},
                    )
                    if resp.status_code in {400, 404}:
                        detail = resp.text.lower()
                        if "not found" in detail or "does not exist" in detail:
                            continue
                    resp.raise_for_status()
                except Exception as exc:
                    errors.append(f"delete {model_name!r}: {exc}")

            # 3. Add models missing from the gateway.
            for model_name in sorted(to_add_names):
                model = desired_by_name[model_name]
                payload: dict[str, Any] = {
                    "model_name": model["model_name"],
                    "litellm_params": model["litellm_params"],
                }
                if model.get("model_info"):
                    payload["model_info"] = model["model_info"]
                try:
                    resp = client.post(f"{base_url}/model/new", headers=headers, json=payload)
                    if resp.status_code in {400, 409}:
                        detail = resp.text.lower()
                        if "already" in detail or "exists" in detail or "duplicate" in detail:
                            continue
                    resp.raise_for_status()
                except Exception as exc:
                    errors.append(f"add {model_name!r}: {exc}")

        removed_model_names = {model_name for model_name, _ in to_delete}
        detail = (
            f"Gateway synced: +{len(to_add_names)} added, "
            f"-{len(removed_model_names)} model(s) removed ({len(to_delete)} row(s)), "
            f"{len(desired_names)} total"
        )
        if errors:
            detail += f"; {len(errors)} error(s): {'; '.join(errors[:3])}"
        if len(errors) > 3:
            detail += f" (and {len(errors) - 3} more)"

        return ProviderGatewaySyncResponse(
            ok=not errors,
            model_count=len(desired_names),
            endpoint=f"{base_url}/model/new",
            detail=detail,
            synced_at=synced_at,
        )

    @staticmethod
    def _build_litellm_hot_model_list(
        model_list: list[dict[str, Any]],
        env_vars: dict[str, str],
    ) -> list[dict[str, Any]]:
        hot_models: list[dict[str, Any]] = []
        for item in model_list:
            if not isinstance(item, dict):
                continue
            cloned = json.loads(json.dumps(item))
            params = cloned.get("litellm_params", {})
            if not isinstance(params, dict):
                continue
            api_key_ref = params.get("api_key")
            if isinstance(api_key_ref, str) and api_key_ref.startswith("os.environ/"):
                env_key = api_key_ref.removeprefix("os.environ/").strip()
                secret = env_vars.get(env_key)
                if not secret:
                    continue
                params["api_key"] = secret
            hot_models.append(cloned)
        return hot_models

    @staticmethod
    def _litellm_base_url() -> str:
        """Return the LiteLLM gateway base URL (no trailing slash, no path suffix)."""
        return (
            os.getenv("LITELLM_INTERNAL_BASE_URL")
            or os.getenv("TEAM_AI_PLATFORM_LITELLM_ADMIN_BASE_URL")
            or "http://localhost:4000"
        ).strip().rstrip("/")

    @staticmethod
    def _litellm_master_key() -> str:
        return (os.getenv("LITELLM_MASTER_KEY") or "").strip()

    # ------------------------------------------------------------------
    # Standardized client (CLI/IDE) runtime configuration
    # ------------------------------------------------------------------

    SUPPORTED_CLIENT_APPS: tuple[str, ...] = ("opencode", "claude-code", "continue", "cursor")

    def build_client_runtime_config(
        self,
        app: str,
        *,
        gateway_base_url: str | None = None,
        api_key: str | None = None,
    ) -> ClientRuntimeConfigResponse:
        """Build a CLI/IDE configuration block from the same canonical model
        registry that powers the LiteLLM gateway.

        This is the single source-of-truth pipeline:
            provider /v1/models -> control-plane state -> LiteLLM model_list
                                                       -> client app config
        Model names returned here are byte-identical to LiteLLM ``model_name``
        entries, so any client consuming this endpoint stays in sync with the
        gateway automatically.
        """
        normalized_app = (app or "").strip().lower()
        if normalized_app not in self.SUPPORTED_CLIENT_APPS:
            raise ValueError(
                f"Unsupported client app '{app}'. Supported: {', '.join(self.SUPPORTED_CLIENT_APPS)}"
            )

        gateway_config, _env_vars, _provider_count, _observability = (
            self._build_litellm_runtime_artifacts()
        )
        model_names = sorted({
            str(entry.get("model_name", "")).strip()
            for entry in gateway_config.get("model_list", [])
            if str(entry.get("model_name", "")).strip()
        })

        base_url = (
            gateway_base_url
            or os.getenv("TEAM_AI_PLATFORM_GATEWAY_BASE_URL")
            or "http://localhost:3000/v1"
        ).strip()
        effective_key = (api_key or os.getenv("LITELLM_MASTER_KEY") or "").strip()

        if normalized_app == "opencode":
            client_config = self._render_opencode_client_config(
                base_url=base_url,
                api_key=effective_key,
                model_names=model_names,
            )
        elif normalized_app == "claude-code":
            client_config = self._render_claude_code_client_config(
                base_url=base_url,
                api_key=effective_key,
                model_names=model_names,
            )
        elif normalized_app == "continue":
            client_config = self._render_continue_client_config(
                base_url=base_url,
                api_key=effective_key,
                model_names=model_names,
            )
        elif normalized_app == "cursor":
            client_config = self._render_cursor_client_config(
                base_url=base_url,
                api_key=effective_key,
                model_names=model_names,
            )
        else:  # pragma: no cover - guarded by SUPPORTED_CLIENT_APPS above
            raise ValueError(f"Unsupported client app '{app}'")

        return ClientRuntimeConfigResponse(
            app=normalized_app,
            gateway_base_url=base_url,
            model_count=len(model_names),
            models=model_names,
            config=client_config,
            generated_at=datetime.now(UTC),
        )

    @staticmethod
    def _render_opencode_client_config(
        *, base_url: str, api_key: str, model_names: list[str], model_by_name: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate OpenCode config pointing to the Team AI Gateway.

        All models are accessed through the team gateway using the user's virtual key.
        The gateway handles routing to upstream providers transparently.
        """
        return {
            "$schema": "https://opencode.ai/config.json",
            "provider": {
                "team-ai-gateway": {
                    "name": "Team AI Gateway",
                    "options": {
                        "baseURL": base_url,
                        "apiKey": api_key or "<your-virtual-key>",
                    },
                    "models": {
                        name: {"name": name}
                        for name in model_names
                    },
                }
            },
        }

    @staticmethod
    def _render_claude_code_client_config(
        *, base_url: str, api_key: str, model_names: list[str]
    ) -> dict[str, Any]:
        """生成 Claude Code (~/.claude/settings.json) 配置块。
        将 ANTHROPIC_BASE_URL 指向团队网关，使 claude 命令透明路由。
        """
        # Claude Code 使用 /v1/chat/completions，需要去掉 /v1 后缀指向网关根
        gateway_root = base_url.rstrip("/")
        if gateway_root.endswith("/v1"):
            gateway_root = gateway_root[:-3]
        return {
            "_install_hint": "将 env 字段合并到 ~/.claude/settings.json，重启 claude 生效",
            "env": {
                "ANTHROPIC_BASE_URL": gateway_root,
                "ANTHROPIC_API_KEY": api_key or "<your-team-key>",
            },
            "_models_available": model_names,
        }

    @staticmethod
    def _render_continue_client_config(
        *, base_url: str, api_key: str, model_names: list[str]
    ) -> dict[str, Any]:
        """生成 Continue.dev (~/.continue/config.json) 配置块。
        每个模型生成一个 provider 条目（OpenAI 兼容模式）。
        """
        return {
            "_install_hint": "将 models 数组合并到 ~/.continue/config.json，保存后 Continue 自动重载",
            "models": [
                {
                    "title": f"Team AI – {m}",
                    "provider": "openai",
                    "model": m,
                    "apiBase": base_url,
                    "apiKey": api_key or "<your-team-key>",
                }
                for m in model_names[:8]  # Continue 建议不超过 8 个以保持 UI 整洁
            ],
        }

    @staticmethod
    def _render_cursor_client_config(
        *, base_url: str, api_key: str, model_names: list[str]
    ) -> dict[str, Any]:
        """生成 Cursor 配置说明（Cursor 通过 Settings > Models 手动配置）。"""
        gateway_root = base_url.rstrip("/")
        if gateway_root.endswith("/v1"):
            gateway_root = gateway_root[:-3]
        return {
            "_install_hint": (
                "在 Cursor Settings > Models > OpenAI API Key 填入 api_key，"
                "在 Override OpenAI Base URL 填入 base_url，保存后 Cursor 自动使用团队网关"
            ),
            "api_key": api_key or "<your-team-key>",
            "base_url": f"{gateway_root}/v1",
            "_models_available": model_names,
        }

    def build_skill_pack_export(self, skill_id: str, target: str) -> SkillPackExportResponse:
        skill = self.get_skill(skill_id)
        if skill is None:
            raise ValueError("Skill not found")

        normalized_target = (target or "").strip().lower()
        if normalized_target not in {"claude-code", "opencode"}:
            raise ValueError("Unsupported target. Supported: claude-code, opencode")

        slug = re.sub(r"[^a-z0-9]+", "-", skill.name.lower()).strip("-") or skill.id
        prompt = (skill.system_prompt or "").strip() or "You are a helpful assistant."
        metadata = {
            "id": skill.id,
            "name": skill.name,
            "category": skill.category,
            "description": skill.description,
            "tags": skill.tags,
            "updated_at": skill.updated_at.isoformat(),
        }
        manifest_json = json.dumps(metadata, ensure_ascii=False, indent=2)

        if normalized_target == "claude-code":
            files = [
                SkillPackFile(
                    path=f".claude/skills/{slug}/SYSTEM_PROMPT.md",
                    description="Claude Code skill system prompt",
                    content=prompt + "\n",
                ),
                SkillPackFile(
                    path=f".claude/skills/{slug}/skill.json",
                    description="Skill metadata manifest",
                    content=manifest_json + "\n",
                ),
            ]
            install_hint = (
                "将文件放入仓库根目录后，Claude Code 可读取 .claude/skills 目录中的技能。"
            )
        else:
            files = [
                SkillPackFile(
                    path=f".opencode/skills/{slug}/prompt.md",
                    description="OpenCode skill prompt template",
                    content=prompt + "\n",
                ),
                SkillPackFile(
                    path=f".opencode/skills/{slug}/skill.json",
                    description="OpenCode skill metadata",
                    content=manifest_json + "\n",
                ),
                SkillPackFile(
                    path=f".opencode/skills/{slug}/README.md",
                    description="OpenCode skill usage guide",
                    content=(
                        f"# {skill.name}\n\n"
                        f"- Category: {skill.category}\n"
                        f"- Tags: {', '.join(skill.tags) if skill.tags else '-'}\n\n"
                        "Generated by Team AI Platform skill export.\n"
                    ),
                ),
            ]
            install_hint = "将目录复制到 .opencode/skills 后，在 OpenCode 中按文件路径引用该技能。"

        return SkillPackExportResponse(
            protocol_version="1.0",
            target=normalized_target,
            skill_id=skill.id,
            skill_name=skill.name,
            generated_at=datetime.now(UTC),
            install_hint=install_hint,
            files=files,
        )

    def _build_litellm_runtime_artifacts(self) -> tuple[dict[str, Any], dict[str, str], int, str]:
        providers = sorted(self.list_providers(enabled=True), key=lambda item: item.id)
        model_entries: list[dict[str, Any]] = []
        env_vars: dict[str, str] = {}
        included_provider_ids: set[str] = set()

        provider_by_id = {provider.id: provider for provider in providers}
        providers_by_type: dict[str, list[ProviderRecord]] = {}
        providers_by_name: dict[str, list[ProviderRecord]] = {}
        for provider in providers:
            providers_by_type.setdefault(provider.provider_type.strip().lower(), []).append(provider)
            providers_by_name.setdefault(provider.name.strip().lower(), []).append(provider)

        active_models = self.list_models(availability="active", limit=None, offset=0)
        for model in active_models:
            provider: ProviderRecord | None = None
            if model.provider_id:
                provider = provider_by_id.get(model.provider_id)

            if provider is None:
                key = (model.provider or "").strip().lower()
                type_matches = providers_by_type.get(key, [])
                if len(type_matches) == 1:
                    provider = type_matches[0]
                elif not type_matches:
                    name_matches = providers_by_name.get(key, [])
                    if len(name_matches) == 1:
                        provider = name_matches[0]

            if provider is None:
                continue

            secret = self._get_provider_secret(provider.id)
            if not secret:
                continue

            included_provider_ids.add(provider.id)
            env_var_name = f"TEAM_AI_LITELLM_PROVIDER_{provider.id.upper()}_API_KEY"
            env_vars[env_var_name] = secret

            model_name = (model.id or "").strip()
            if not model_name:
                continue
            upstream_model = (model.upstream_model or model_name).strip()
            litellm_model_ref = self._build_litellm_model_ref(provider, upstream_model)
            model_info = self._build_litellm_model_info(provider)
            entry: dict[str, Any] = {
                "model_name": model_name,
                "litellm_params": {
                    "model": litellm_model_ref,
                    "api_base": provider.base_url,
                    "api_key": f"os.environ/{env_var_name}",
                },
            }
            if model_info:
                entry["model_info"] = model_info
            model_entries.append(entry)

        # Compatibility fallback: if no models are registered yet, keep
        # deriving model list from provider state to preserve old behavior.
        if not model_entries:
            provider_models: list[tuple[ProviderRecord, list[str]]] = []

            for provider in providers:
                model_ids = self._provider_model_ids_from_state(provider)
                provider_models.append((provider, model_ids))

            canonical_model_counts = Counter(
                model_id.strip()
                for _provider, model_ids in provider_models
                for model_id in model_ids
                if model_id and model_id.strip()
            )

            for provider, model_ids in provider_models:
                secret = self._get_provider_secret(provider.id)
                if not secret:
                    continue

                included_provider_ids.add(provider.id)
                env_var_name = f"TEAM_AI_LITELLM_PROVIDER_{provider.id.upper()}_API_KEY"
                env_vars[env_var_name] = secret

                for model_id in model_ids:
                    litellm_model_ref = self._build_litellm_model_ref(provider, model_id)
                    model_info = self._build_litellm_model_info(provider)
                    for model_alias in self._build_provider_model_names(
                        provider,
                        model_id,
                        canonical_model_counts,
                    ):
                        entry = {
                            "model_name": model_alias,
                            "litellm_params": {
                                "model": litellm_model_ref,
                                "api_base": provider.base_url,
                                "api_key": f"os.environ/{env_var_name}",
                            },
                        }
                        if model_info:
                            entry["model_info"] = model_info
                        model_entries.append(entry)

        model_entries = sorted(model_entries, key=lambda entry: str(entry.get("model_name", "")))
        observability_backend, litellm_settings, observability_env_vars = self._build_observability_profile()
        env_vars.update(observability_env_vars)
        included_provider_count = len(included_provider_ids)

        config = {
            "model_list": model_entries,
            "general_settings": {
                "master_key": "os.environ/LITELLM_MASTER_KEY",
            },
        }
        if litellm_settings:
            config["litellm_settings"] = litellm_settings
        return config, env_vars, included_provider_count, observability_backend

    @staticmethod
    def _build_observability_profile() -> tuple[str, dict[str, Any], dict[str, str]]:
        backend = os.getenv("TEAM_AI_PLATFORM_OBSERVABILITY_BACKEND", "langfuse").strip().lower() or "langfuse"
        if backend in {"none", "off", "disabled"}:
            return "none", {}, {}

        if backend == "langfuse":
            public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
            secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
            if not public_key or not secret_key:
                return "none", {}, {}

            env_vars = {
                "LANGFUSE_PUBLIC_KEY": public_key,
                "LANGFUSE_SECRET_KEY": secret_key,
            }
            host = os.getenv("LANGFUSE_HOST", "").strip()
            if host:
                env_vars["LANGFUSE_HOST"] = host

            return "langfuse", {
                "success_callback": ["langfuse"],
                "failure_callback": ["langfuse"],
            }, env_vars

        if backend == "helicone":
            helicone_key = os.getenv("HELICONE_API_KEY", "").strip()
            if not helicone_key:
                return "none", {}, {}

            env_vars = {"HELICONE_API_KEY": helicone_key}
            helicone_base_url = os.getenv("HELICONE_BASE_URL", "").strip()
            if helicone_base_url:
                env_vars["HELICONE_BASE_URL"] = helicone_base_url

            return "helicone", {
                "success_callback": ["helicone"],
                "failure_callback": ["helicone"],
            }, env_vars

        return "none", {}, {}

    def _resolve_litellm_output_paths(self, output_dir: str | None = None) -> tuple[Path, Path]:
        if output_dir:
            target_dir = Path(output_dir)
        else:
            target_dir = Path(__file__).resolve().parents[2] / "litellm"
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / "config.yaml", target_dir / ".env.litellm"

    def _provider_model_ids_from_state(self, provider: ProviderRecord) -> list[str]:
        raw_model_ids = provider.metadata.get("model_ids") if isinstance(provider.metadata, dict) else None
        if isinstance(raw_model_ids, list):
            normalized = sorted({str(item).strip() for item in raw_model_ids if str(item).strip()})
            # Backward compatibility: early presets stored template keys like
            # "qwen_bailian" in model_ids, which is not a real upstream model.
            if provider.provider_type == "qwen":
                normalized = ["qwen-plus" if item == "qwen_bailian" else item for item in normalized]
                normalized = sorted(set(normalized))
            if normalized:
                return normalized
        return [self._default_provider_model_id(provider)]

    def _discover_provider_model_ids(self, provider: ProviderRecord, api_key: str) -> list[str]:
        discovered = self._discover_provider_model_ids_raw(
            provider_type=provider.provider_type,
            base_url=provider.base_url,
            api_key=api_key,
        )

        # Bailian can expose both Qwen and non-Qwen models. Restricting to
        # Qwen-only families should only apply to the dedicated qwen_coder preset.
        if provider.provider_type == "qwen" and provider.preset_key == "qwen_coder":
            return self._filter_qwen_model_ids(discovered)
        return discovered

    def _discover_provider_model_ids_raw(self, provider_type: str, base_url: str, api_key: str) -> list[str]:
        endpoint = self._models_endpoint(base_url)
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(endpoint, headers=headers)
            if response.status_code >= 400:
                return []
            payload = response.json()
        except Exception:
            return []

        data = payload.get("data", []) if isinstance(payload, dict) else []
        model_ids = [item.get("id") for item in data if isinstance(item, dict) and isinstance(item.get("id"), str)]
        return sorted(set(model_ids))

    @staticmethod
    def _is_qwen_family_model(model_id: str) -> bool:
        lowered = model_id.strip().lower()
        if not lowered:
            return False
        target = lowered.split("/", 1)[-1]
        return target.startswith(("qwen", "qwq", "qvq", "wan"))

    @staticmethod
    def _qwen_model_family_key(model_id: str) -> str:
        # Group versioned aliases (latest/date/mmdd) under the same base family.
        target = model_id.strip().split("/", 1)[-1]
        target = re.sub(r"-latest$", "", target, flags=re.IGNORECASE)
        target = re.sub(r"-(?:\d{4}-\d{2}-\d{2}|\d{8}|\d{4})$", "", target)
        return target.lower()

    @staticmethod
    def _qwen_history_sort_key(model_id: str) -> int:
        target = model_id.strip().split("/", 1)[-1]
        match = re.search(r"-(\d{4}-\d{2}-\d{2}|\d{8}|\d{4})$", target)
        if not match:
            return -1
        token = match.group(1)
        if "-" in token:
            return int(token.replace("-", ""))
        if len(token) == 8:
            return int(token)
        # mmdd style suffix (e.g. 0919) has lower confidence than explicit dates.
        return int(f"1{token}")

    def _filter_qwen_model_ids(self, model_ids: list[str]) -> list[str]:
        families: dict[str, dict[str, Any]] = {}

        for model_id in model_ids:
            normalized = model_id.strip()
            if not normalized or not self._is_qwen_family_model(normalized):
                continue
            family = self._qwen_model_family_key(normalized)
            entry = families.setdefault(family, {"stable": set(), "latest": set(), "history": []})
            lowered = normalized.lower()
            if lowered.endswith("-latest"):
                entry["latest"].add(normalized)
                continue
            history_key = self._qwen_history_sort_key(normalized)
            if history_key >= 0:
                entry["history"].append((history_key, normalized))
            else:
                entry["stable"].add(normalized)

        selected: set[str] = set()
        for entry in families.values():
            # DashScope exposes hundreds of legacy/third-party aliases.
            # Keep only families that have a stable release track (latest/date).
            if not entry["latest"] and not entry["history"]:
                continue

            selected.update(entry["latest"])
            # Preserve base stable alias for caller convenience.
            selected.update(entry["stable"])
            history = sorted(entry["history"], key=lambda item: (item[0], item[1]), reverse=True)
            selected.update(model for _score, model in history[:3])

        return sorted(selected)

    @staticmethod
    def _default_provider_model_id(provider: ProviderRecord) -> str:
        if provider.provider_type == "deepseek":
            return "deepseek-chat"
        if provider.provider_type == "qwen" or provider.preset_key == "qwen_bailian":
            # Preset key identifies provider template, not upstream model id.
            # DashScope OpenAI-compatible chat should use a concrete model name.
            return "qwen-plus"
        if provider.preset_key:
            return provider.preset_key
        return "model"

    @staticmethod
    def _build_provider_model_names(
        provider: ProviderRecord,
        model_id: str,
        canonical_model_counts: Counter[str],
    ) -> list[str]:
        """Return the model_name(s) to register in the LiteLLM model_list.

        The name a client sends as ``model`` in its request must match one of
        these.  We deliberately expose only the canonical upstream model ID
        (e.g. ``deepseek-v4-pro``).  Provider-specific routing prefixes like
        ``openai/`` live exclusively in ``litellm_params.model`` and are never
        surfaced to callers — this keeps the gateway provider-agnostic.
        """
        canonical = model_id.strip()
        if not canonical:
            return []

        # Use the upstream model ID directly when there is no cross-provider
        # collision; fall back to a namespaced form only to resolve conflicts.
        if canonical_model_counts.get(canonical, 0) <= 1:
            return [canonical]

        namespace = provider.preset_key or provider.provider_type or provider.id
        namespace = re.sub(r"[^a-zA-Z0-9_-]+", "-", namespace).strip("-").lower() or "provider"
        return [f"{namespace}/{canonical}"]

    @staticmethod
    def _build_litellm_model_ref(provider: ProviderRecord, model_id: str) -> str:
        model_value = model_id.strip()
        if provider.provider_type == "deepseek":
            normalized = model_value.removeprefix("deepseek/").removeprefix("openai/")
            return f"openai/{normalized}"
        if provider.api_format == "openai":
            return model_value if model_value.startswith("openai/") else f"openai/{model_value}"
        if "/" in model_value:
            return model_value
        return f"{provider.provider_type}/{model_value}"

    @staticmethod
    def _build_litellm_model_info(provider: ProviderRecord) -> dict[str, Any]:
        """Build the ``model_info`` block for a LiteLLM model_list entry.

        LiteLLM exposes these flags through ``/v1/models`` and uses them
        internally when routing specialised endpoints such as ``/v1/responses``
        (OpenAI Responses API).  Providers that only support the standard
        OpenAI chat-completions format must have ``supports_response_schema``
        set to ``False`` so that clients like OpenCode do not attempt the
        Responses API path for them.
        """
        is_openai_format = (
            provider.provider_type in {"deepseek", "openai"}
            or provider.api_format == "openai"
        )
        # Providers that advertise a native Responses API endpoint.
        is_native_responses_api = provider.api_format == "openai_responses"

        if not is_openai_format and not is_native_responses_api:
            return {}

        return {
            # Standard chat-completions capabilities.
            "supports_function_calling": True,
            "supports_tool_choice": True,
            # Responses API (OpenAI o-series feature) — only enable for
            # providers that explicitly expose it.  For all other OpenAI-
            # compatible backends (DeepSeek, custom gateways, etc.) keep it
            # off so clients fall back to /v1/chat/completions.
            "supports_response_schema": is_native_responses_api,
        }

    @staticmethod
    def _is_team_ai_managed_model_entry(entry: Any) -> bool:
        if not isinstance(entry, dict):
            return False
        params = entry.get("litellm_params")
        if not isinstance(params, dict):
            return False
        api_key_ref = params.get("api_key")
        if not isinstance(api_key_ref, str):
            return False
        return "os.environ/TEAM_AI_LITELLM_PROVIDER_" in api_key_ref
