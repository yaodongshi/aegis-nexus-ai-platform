from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from itertools import count
import json
import os
from typing import Any
from uuid import uuid4

import httpx
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
    ProviderCreateRequest,
    ProviderModelDiscoveryResponse,
    ProviderRecord,
    ProviderSyncRequest,
    ProviderUpdateRequest,
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
    providers: dict[str, ProviderRecord] = field(default_factory=dict)
    provider_secrets: dict[str, str] = field(default_factory=dict)
    _model_seq: count = field(default_factory=lambda: count(1))
    _key_seq: count = field(default_factory=lambda: count(1))
    _skill_seq: count = field(default_factory=lambda: count(1))
    _session_seq: count = field(default_factory=lambda: count(1))
    _policy_seq: count = field(default_factory=lambda: count(1))
    _approval_seq: count = field(default_factory=lambda: count(1))
    _provider_seq: count = field(default_factory=lambda: count(1))

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
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO backend_skills (
                        skill_id, name, version, owner_id, metadata,
                        policy, dependencies, signature, status, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        skill_id,
                        payload.package_name,
                        payload.version,
                        None,
                        Json(metadata),
                        Json(policy),
                        Json([]),
                        sha256(f"{payload.package_name}:{payload.version}".encode("utf-8")).hexdigest(),
                        "dev",
                        now,
                        now,
                    ),
                )
            return SkillPublishResponse(skill_id=skill_id, version=payload.version, lifecycle_status="dev")

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
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT skill_id, name, version, owner_id, metadata, policy,
                           dependencies, signature, status, created_at, updated_at
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
                    SELECT skill_id, name, version, owner_id, metadata, policy,
                           dependencies, signature, status, created_at, updated_at
                    FROM backend_skills WHERE skill_id = %s
                    """,
                    (skill_id,),
                )
                row = cur.fetchone()
            return self._skill_from_row(row) if row else None
        return self.skills.get(skill_id)

    def rollback_skill(self, skill_id: str) -> SkillRecord | None:
        if self._db_enabled:
            updated_at = datetime.now(UTC)
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE backend_skills
                    SET status = 'rollback', updated_at = %s
                    WHERE skill_id = %s
                    RETURNING skill_id, name, version, owner_id, metadata, policy,
                              dependencies, signature, status, created_at, updated_at
                    """,
                    (updated_at, skill_id),
                )
                row = cur.fetchone()
            return self._skill_from_row(row) if row else None

        record = self.skills.get(skill_id)
        if record is None:
            return None
        updated = record.model_copy(update={"status": "rollback", "updated_at": datetime.now(UTC)})
        self.skills[skill_id] = updated
        return updated

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

    def list_providers(
        self,
        *,
        scope: str | None = None,
        app: str | None = None,
        enabled: bool | None = None,
    ) -> list[ProviderRecord]:
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
                        Json(payload.metadata),
                        payload.api_key,
                        now,
                        now,
                    ),
                )
                row = cur.fetchone()
            return self._provider_from_row(row)

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
            metadata=payload.metadata,
            api_key_masked=self._mask_key(payload.api_key),
            created_at=now,
            updated_at=now,
        )
        self.providers[provider_id] = record
        self.provider_secrets[provider_id] = payload.api_key
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
            updated = existing.model_copy(update={k: v for k, v in data.items() if k != "api_key"} | {"updated_at": datetime.now(UTC)})
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
            return self._provider_from_row(row)

        data = payload.model_dump(exclude_none=True)
        updated = existing.model_copy(update={k: v for k, v in data.items() if k != "api_key"} | {"updated_at": datetime.now(UTC)})
        if "api_key" in data:
            self.provider_secrets[provider_id] = data["api_key"]
            updated = updated.model_copy(update={"api_key_masked": self._mask_key(data["api_key"])})
        self.providers[provider_id] = updated
        return updated

    def delete_provider(self, provider_id: str) -> bool:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("DELETE FROM backend_providers WHERE provider_id = %s", (provider_id,))
                return cur.rowcount > 0
        existed = provider_id in self.providers
        self.providers.pop(provider_id, None)
        self.provider_secrets.pop(provider_id, None)
        return existed

    def sync_provider(self, provider_id: str, payload: ProviderSyncRequest) -> ProviderRecord | None:
        existing = self.get_provider(provider_id)
        if existing is None:
            return None
        update_payload = ProviderUpdateRequest(
            scope="unified",
            apps=payload.target_apps or existing.apps,
        )
        return self.update_provider(provider_id, update_payload)

    def discover_provider_models(self, provider_id: str) -> ProviderModelDiscoveryResponse:
        provider = self.get_provider(provider_id)
        if provider is None:
            raise ValueError("Provider not found")
        api_key = self._get_provider_secret(provider_id)
        if not api_key:
            raise ValueError("Provider API key is missing")

        endpoint = self._models_endpoint(provider.base_url)
        headers = {"Authorization": f"Bearer {api_key}"}
        with httpx.Client(timeout=15.0) as client:
            response = client.get(endpoint, headers=headers)

        if response.status_code >= 400:
            raise ValueError(f"Provider endpoint error: HTTP {response.status_code}")

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise ValueError("Provider response is not valid JSON") from exc

        data = payload.get("data", []) if isinstance(payload, dict) else []
        model_ids: list[str] = []
        for row in data:
            if isinstance(row, dict) and isinstance(row.get("id"), str):
                model_ids.append(row["id"])

        return ProviderModelDiscoveryResponse(
            provider_id=provider_id,
            endpoint=endpoint,
            models=sorted(set(model_ids)),
            fetched_at=datetime.now(UTC),
        )

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
            "provider": self._provider_seq,
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
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backend_skills (
                    skill_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    owner_id TEXT,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    policy JSONB NOT NULL DEFAULT '{}'::jsonb,
                    dependencies JSONB NOT NULL DEFAULT '[]'::jsonb,
                    signature TEXT,
                    status TEXT NOT NULL DEFAULT 'dev',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
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

    @staticmethod
    def _skill_from_row(row: tuple[Any, ...]) -> SkillRecord:
        metadata = row[4] if isinstance(row[4], dict) else {}
        policy = row[5] if isinstance(row[5], dict) else {}
        dependencies = row[6] if isinstance(row[6], list) else []
        return SkillRecord(
            id=row[0],
            name=row[1],
            version=row[2],
            owner_id=row[3],
            metadata=metadata,
            policy=policy,
            dependencies=dependencies,
            signature=row[7],
            status=row[8],
            created_at=row[9],
            updated_at=row[10],
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
        if normalized.endswith("/v1"):
            return f"{normalized}/models"
        return f"{normalized}/v1/models"

    def _provider_from_row(self, row: tuple[Any, ...]) -> ProviderRecord:
        apps = row[6] if isinstance(row[6], list) else []
        metadata = row[10] if isinstance(row[10], dict) else {}
        api_key = row[11] if isinstance(row[11], str) else ""
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
            api_key_masked=self._mask_key(api_key) if api_key else None,
            created_at=row[12],
            updated_at=row[13],
        )
