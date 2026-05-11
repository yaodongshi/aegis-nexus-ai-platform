from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from itertools import count
import os
from typing import Any
from uuid import uuid4

import psycopg2
from psycopg2.extras import Json

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
    db_dsn: str | None = None
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

    def __post_init__(self) -> None:
        if self.db_dsn is None:
            env_dsn = os.getenv("TEAM_AI_PLATFORM_DB_DSN", "").strip()
            self.db_dsn = env_dsn or None

    def seed_defaults(self) -> None:
        now = datetime.now(UTC)
        if self._db_enabled:
            self._ensure_schema()
            self.register_model(
                ModelRegisterRequest(
                    provider="openai",
                    name="GPT-4o",
                    endpoint="https://api.openai.com/v1/chat/completions",
                    context_window=128000,
                    cost_tier="high",
                    tags=["chat", "code"],
                    labels={"team": "platform", "tier": "prod"},
                    quota=None,
                )
            )
        elif not self.models:
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

    def list_models(
        self,
        *,
        provider: str | None = None,
        availability: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ModelRecord]:
        if self._db_enabled:
            query = (
                "SELECT model_id, provider, name, endpoint, context_window, cost_tier, "
                "availability, tags, labels, quota, created_at, updated_at "
                "FROM backend_models WHERE 1=1"
            )
            params: list[Any] = []
            if provider is not None:
                query += " AND provider = %s"
                params.append(provider)
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
        if availability is not None:
            records = [record for record in records if record.availability == availability]
        if offset > 0:
            records = records[offset:]
        if limit is not None:
            records = records[:limit]
        return records

    def register_model(self, payload: ModelRegisterRequest) -> ModelRecord:
        now = datetime.now(UTC)
        model_id = payload.name.lower().replace(" ", "-")
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_models (
                        model_id, provider, name, endpoint, context_window,
                        cost_tier, availability, tags, labels, quota, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (model_id) DO UPDATE SET
                        provider = EXCLUDED.provider,
                        name = EXCLUDED.name,
                        endpoint = EXCLUDED.endpoint,
                        context_window = EXCLUDED.context_window,
                        cost_tier = EXCLUDED.cost_tier,
                        availability = EXCLUDED.availability,
                        tags = EXCLUDED.tags,
                        labels = EXCLUDED.labels,
                        quota = EXCLUDED.quota,
                        updated_at = EXCLUDED.updated_at
                    RETURNING model_id, provider, name, endpoint, context_window,
                              cost_tier, availability, tags, labels, quota, created_at, updated_at
                    """,
                    (
                        model_id,
                        payload.provider,
                        payload.name,
                        payload.endpoint,
                        payload.context_window,
                        payload.cost_tier,
                        "active",
                        Json(payload.tags),
                        Json(payload.labels),
                        payload.quota,
                        now,
                        now,
                    ),
                )
                row = cur.fetchone()
            return self._model_from_row(row)

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
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT model_id, provider, name, endpoint, context_window, cost_tier,
                           availability, tags, labels, quota, created_at, updated_at
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
                        endpoint = %s,
                        context_window = %s,
                        cost_tier = %s,
                        availability = %s,
                        tags = %s,
                        labels = %s,
                        quota = %s,
                        updated_at = %s
                    WHERE model_id = %s
                    """,
                    (
                        updated.endpoint,
                        updated.context_window,
                        updated.cost_tier,
                        updated.availability,
                        Json(updated.tags),
                        Json(updated.labels),
                        updated.quota,
                        updated.updated_at,
                        model_id,
                    ),
                )
            return updated

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
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_keys (
                        key_id, key_hash, user_id, project_id, scope,
                        expire_at, quota, status, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'active', %s, %s)
                    RETURNING key_id, key_hash, user_id, project_id, scope,
                              expire_at, quota, status, created_at, updated_at
                    """,
                    (
                        key_id,
                        key_hash,
                        payload.user_id,
                        payload.project_id,
                        payload.scope,
                        payload.expire_at,
                        payload.quota,
                        now,
                        now,
                    ),
                )
                row = cur.fetchone()
            record = self._key_from_row(row)
            response = KeyIssueResponse(
                key_id=key_id,
                key_secret=key_secret,
                status=record.status,
                expire_at=record.expire_at,
            )
            return record, response

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
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT key_id, key_hash, user_id, project_id, scope,
                           expire_at, quota, status, created_at, updated_at
                    FROM backend_keys ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()
            return [self._key_from_row(row) for row in rows]
        return list(self.keys.values())

    def revoke_key(self, key_id: str) -> KeyRecord | None:
        if self._db_enabled:
            updated_at = datetime.now(UTC)
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_keys
                    SET status = 'revoked', updated_at = %s
                    WHERE key_id = %s
                    RETURNING key_id, key_hash, user_id, project_id, scope,
                              expire_at, quota, status, created_at, updated_at
                    """,
                    (updated_at, key_id),
                )
                row = cur.fetchone()
            return self._key_from_row(row) if row else None

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
        if self._db_enabled:
            return f"{prefix}_{uuid4().hex[:12]}"
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

    def _ensure_schema(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_models (
                    model_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    name TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    context_window INTEGER NOT NULL,
                    cost_tier TEXT NOT NULL,
                    availability TEXT NOT NULL DEFAULT 'active',
                    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                    labels JSONB NOT NULL DEFAULT '{}'::jsonb,
                    quota BIGINT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_keys (
                    key_id TEXT PRIMARY KEY,
                    key_hash TEXT NOT NULL UNIQUE,
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

    @staticmethod
    def _model_from_row(row: tuple[Any, ...]) -> ModelRecord:
        tags = row[7] if isinstance(row[7], list) else []
        labels = row[8] if isinstance(row[8], dict) else {}
        return ModelRecord(
            id=row[0],
            provider=row[1],
            name=row[2],
            endpoint=row[3],
            context_window=row[4],
            cost_tier=row[5],
            availability=row[6],
            tags=tags,
            labels=labels,
            quota=row[9],
            created_at=row[10],
            updated_at=row[11],
        )

    @staticmethod
    def _key_from_row(row: tuple[Any, ...]) -> KeyRecord:
        return KeyRecord(
            id=row[0],
            key_hash=row[1],
            user_id=row[2],
            project_id=row[3],
            scope=row[4],
            expire_at=row[5],
            quota=row[6],
            status=row[7],
            created_at=row[8],
            updated_at=row[9],
        )
