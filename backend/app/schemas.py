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
    name: str
    endpoint: str
    context_window: int
    cost_tier: str
    availability: str = "active"
    tags: list[str] = Field(default_factory=list)
    labels: dict[str, Any] = Field(default_factory=dict)
    quota: int | None = None
    created_at: datetime
    updated_at: datetime


class ModelRegisterRequest(BaseModel):
    provider: str
    name: str
    endpoint: str
    context_window: int
    cost_tier: str
    tags: list[str] = Field(default_factory=list)
    labels: dict[str, Any] = Field(default_factory=dict)
    quota: int | None = None


class ModelUpdateRequest(BaseModel):
    endpoint: str | None = None
    context_window: int | None = None
    cost_tier: str | None = None
    availability: str | None = None
    tags: list[str] | None = None
    labels: dict[str, Any] | None = None
    quota: int | None = None


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


class SkillPublishRequest(BaseModel):
    package_name: str
    version: str
    skill_yaml: str
    policy_json: str
    tests_archive: str | None = None


class SkillRecord(BaseModel):
    id: str
    name: str
    version: str
    owner_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    signature: str | None = None
    status: Literal["dev", "stage", "prod", "rollback"] = "dev"
    created_at: datetime
    updated_at: datetime


class SkillPublishResponse(BaseModel):
    skill_id: str
    version: str
    lifecycle_status: str


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


class ProviderUpdateRequest(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    preset_key: str | None = None
    scope: Literal["app", "unified"] | None = None
    apps: list[str] | None = None
    api_format: Literal["openai", "anthropic", "openai_responses"] | None = None
    notes: str | None = None
    enabled: bool | None = None
    metadata: dict[str, Any] | None = None


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
    api_key_masked: str | None = None
    created_at: datetime
    updated_at: datetime


class ProviderSyncRequest(BaseModel):
    target_apps: list[str] = Field(default_factory=list)


class ProviderModelDiscoveryResponse(BaseModel):
    provider_id: str
    endpoint: str
    models: list[str] = Field(default_factory=list)
    fetched_at: datetime


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
    auto_commit: bool = True


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
