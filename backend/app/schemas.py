from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


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
    user_id: str
    project_id: str | None = None
    scope: str
    expire_at: datetime | None = None
    quota: int | None = None


class KeyRecord(BaseModel):
    id: str
    key_hash: str
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
