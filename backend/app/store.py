from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from itertools import count
from typing import Any
from uuid import uuid4

from .schemas import (
    ApprovalRecord,
    ApprovalSubmitRequest,
    KeyIssueRequest,
    KeyIssueResponse,
    KeyRecord,
    ModelRecord,
    ModelRegisterRequest,
    ModelUpdateRequest,
    PolicyRecord,
    PolicyUpsertRequest,
    SessionCreateRequest,
    SessionRecord,
    SessionUpdateRequest,
    SkillPublishRequest,
    SkillPublishResponse,
    SkillRecord,
)


@dataclass
class PlatformStore:
    models: dict[str, ModelRecord] = field(default_factory=dict)
    keys: dict[str, KeyRecord] = field(default_factory=dict)
    skills: dict[str, SkillRecord] = field(default_factory=dict)
    sessions: dict[str, SessionRecord] = field(default_factory=dict)
    policies: dict[str, PolicyRecord] = field(default_factory=dict)
    approvals: dict[str, ApprovalRecord] = field(default_factory=dict)
    _model_seq: count = field(default_factory=lambda: count(1))
    _key_seq: count = field(default_factory=lambda: count(1))
    _skill_seq: count = field(default_factory=lambda: count(1))
    _session_seq: count = field(default_factory=lambda: count(1))
    _policy_seq: count = field(default_factory=lambda: count(1))
    _approval_seq: count = field(default_factory=lambda: count(1))

    def seed_defaults(self) -> None:
        if self.models:
            return
        now = datetime.now(UTC)
        self.models["gpt-4o"] = ModelRecord(
            id="gpt-4o",
            provider="openai",
            name="GPT-4o",
            endpoint="https://api.openai.com/v1/chat/completions",
            context_window=128000,
            cost_tier="high",
            availability="active",
            tags=["chat", "code"],
            labels={"team": "platform", "tier": "prod"},
            quota=None,
            created_at=now,
            updated_at=now,
        )
        self.policies["default-approval"] = PolicyRecord(
            id=self._next_id("policy"),
            name="default-approval",
            type="approval",
            rules={"actions": ["db_migrate", "prod_deploy"]},
            status="active",
            created_at=now,
            updated_at=now,
        )

    def list_models(self) -> list[ModelRecord]:
        return list(self.models.values())

    def register_model(self, payload: ModelRegisterRequest) -> ModelRecord:
        now = datetime.now(UTC)
        model_id = payload.name.lower().replace(" ", "-")
        record = ModelRecord(
            id=model_id,
            provider=payload.provider,
            name=payload.name,
            endpoint=payload.endpoint,
            context_window=payload.context_window,
            cost_tier=payload.cost_tier,
            availability="active",
            tags=payload.tags,
            labels=payload.labels,
            quota=payload.quota,
            created_at=now,
            updated_at=now,
        )
        self.models[model_id] = record
        return record

    def get_model(self, model_id: str) -> ModelRecord | None:
        return self.models.get(model_id)

    def update_model(self, model_id: str, payload: ModelUpdateRequest) -> ModelRecord | None:
        record = self.models.get(model_id)
        if record is None:
            return None
        updated = record.model_copy(update=payload.model_dump(exclude_none=True) | {"updated_at": datetime.now(UTC)})
        self.models[model_id] = updated
        return updated

    def issue_key(self, payload: KeyIssueRequest) -> tuple[KeyRecord, KeyIssueResponse]:
        now = datetime.now(UTC)
        key_id = self._next_id("key")
        key_secret = f"sk-virtual-{uuid4().hex[:12]}"
        key_hash = sha256(key_secret.encode("utf-8")).hexdigest()
        record = KeyRecord(
            id=key_id,
            key_hash=key_hash,
            user_id=payload.user_id,
            project_id=payload.project_id,
            scope=payload.scope,
            expire_at=payload.expire_at,
            quota=payload.quota,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.keys[key_id] = record
        response = KeyIssueResponse(
            key_id=key_id,
            key_secret=key_secret,
            status=record.status,
            expire_at=record.expire_at,
        )
        return record, response

    def list_keys(self) -> list[KeyRecord]:
        return list(self.keys.values())

    def revoke_key(self, key_id: str) -> KeyRecord | None:
        record = self.keys.get(key_id)
        if record is None:
            return None
        updated = record.model_copy(update={"status": "revoked", "updated_at": datetime.now(UTC)})
        self.keys[key_id] = updated
        return updated

    def publish_skill(self, payload: SkillPublishRequest) -> SkillPublishResponse:
        now = datetime.now(UTC)
        skill_id = self._next_id("skill")
        metadata = {"package_name": payload.package_name, "skill_yaml": payload.skill_yaml}
        policy = self._parse_json_like(payload.policy_json)
        record = SkillRecord(
            id=skill_id,
            name=payload.package_name,
            version=payload.version,
            owner_id=None,
            metadata=metadata,
            policy=policy,
            dependencies=[],
            signature=sha256(f"{payload.package_name}:{payload.version}".encode("utf-8")).hexdigest(),
            status="dev",
            created_at=now,
            updated_at=now,
        )
        self.skills[skill_id] = record
        return SkillPublishResponse(skill_id=skill_id, version=payload.version, lifecycle_status=record.status)

    def list_skills(self) -> list[SkillRecord]:
        return list(self.skills.values())

    def get_skill(self, skill_id: str) -> SkillRecord | None:
        return self.skills.get(skill_id)

    def rollback_skill(self, skill_id: str) -> SkillRecord | None:
        record = self.skills.get(skill_id)
        if record is None:
            return None
        updated = record.model_copy(update={"status": "rollback", "updated_at": datetime.now(UTC)})
        self.skills[skill_id] = updated
        return updated

    def create_session(self, payload: SessionCreateRequest) -> SessionRecord:
        now = datetime.now(UTC)
        session_id = self._next_id("session")
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
        return list(self.sessions.values())

    def get_session(self, session_id: str) -> SessionRecord | None:
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, payload: SessionUpdateRequest) -> SessionRecord | None:
        record = self.sessions.get(session_id)
        if record is None:
            return None
        updated = record.model_copy(update=payload.model_dump(exclude_none=True) | {"updated_at": datetime.now(UTC)})
        self.sessions[session_id] = updated
        return updated

    def upsert_policy(self, payload: PolicyUpsertRequest) -> PolicyRecord:
        now = datetime.now(UTC)
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
        return list(self.policies.values())

    def get_policy(self, policy_id: str) -> PolicyRecord | None:
        return self.policies.get(policy_id)

    def submit_approval(self, payload: ApprovalSubmitRequest) -> ApprovalRecord:
        now = datetime.now(UTC)
        approval_id = self._next_id("approval")
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
        return list(self.approvals.values())

    def get_approval(self, approval_id: str) -> ApprovalRecord | None:
        return self.approvals.get(approval_id)

    def _next_id(self, prefix: str) -> str:
        seq_map = {
            "model": self._model_seq,
            "key": self._key_seq,
            "skill": self._skill_seq,
            "session": self._session_seq,
            "policy": self._policy_seq,
            "approval": self._approval_seq,
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
