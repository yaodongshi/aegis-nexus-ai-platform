from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from itertools import count
import json
import logging
import os
from pathlib import Path
import re
from time import perf_counter
from typing import Any
from uuid import uuid4

import httpx
import psycopg2
import yaml
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
    ProviderBatchProbeItem,
    ProviderBatchProbeRequest,
    ProviderBatchProbeResponse,
    ProviderBatchDeleteRequest,
    ProviderBatchDeleteResponse,
    ProviderBatchUpdateRequest,
    ProviderBatchUpdateResponse,
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
    PolicyRecord,
    PolicyUpsertRequest,
    SessionCreateRequest,
    SessionRecord,
    SessionUpdateRequest,
    SkillPublishRequest,
    SkillPublishResponse,
    SkillRecord,
    V2KeyPolicyRecord,
    V2KeyPolicyUpsertRequest,
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
    policies: dict[str, PolicyRecord] = field(default_factory=dict)
    approvals: dict[str, ApprovalRecord] = field(default_factory=dict)
    providers: dict[str, ProviderRecord] = field(default_factory=dict)
    provider_secrets: dict[str, str] = field(default_factory=dict)
    provider_probe_logs: dict[str, list[ProviderProbeLogRecord]] = field(default_factory=dict)
    v2_virtual_keys: dict[str, V2VirtualKeyRecord] = field(default_factory=dict)
    v2_key_policies: dict[str, V2KeyPolicyRecord] = field(default_factory=dict)
    # M1.3: Virtual Key Lifecycle - Audit logging and usage tracking
    key_audit_logs: dict[str, list[dict]] = field(default_factory=dict)
    key_usage_stats: dict[str, dict] = field(default_factory=dict)
    _model_seq: count = field(default_factory=lambda: count(1))
    _key_seq: count = field(default_factory=lambda: count(1))
    _skill_seq: count = field(default_factory=lambda: count(1))
    _session_seq: count = field(default_factory=lambda: count(1))
    _policy_seq: count = field(default_factory=lambda: count(1))
    _approval_seq: count = field(default_factory=lambda: count(1))
    _provider_seq: count = field(default_factory=lambda: count(1))
    _provider_probe_seq: count = field(default_factory=lambda: count(1))
    _v2_key_policy_seq: count = field(default_factory=lambda: count(1))
    _schema_ensured: bool = False

    def __post_init__(self) -> None:
        if self.db_dsn is None:
            env_dsn = os.getenv("TEAM_AI_PLATFORM_DB_DSN", "").strip()
            self.db_dsn = env_dsn or None
        if self._db_enabled:
            self._ensure_schema_once()

    def seed_defaults(self) -> None:
        now = datetime.now(UTC)
        if self._db_enabled:
            self._ensure_schema_once()
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
            # Also store in memory for audit/stats queries (M1.3 requirement)
            self.keys[key_id] = record
            self._record_audit_log(key_id, "issued", payload.user_id, {"label": payload.label, "scope": payload.scope})
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
        self._record_audit_log(key_id, "issued", payload.user_id, {"label": payload.label, "scope": payload.scope})
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
            record = self._key_from_row(row) if row else None
            if record is not None:
                self.keys[key_id] = record
                self._record_audit_log(key_id, "revoked", None, {})
            return record

        record = self.keys.get(key_id)
        if record is None:
            return None
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
                    INSERT INTO cp_virtual_key (
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
                    FROM cp_virtual_key
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

    def get_v2_virtual_key(self, key_id: str) -> V2VirtualKeyRecord | None:
        if self._db_enabled:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT key_id, team_id, alias, owner_type, owner_id, status,
                           expires_at, rotated_from, created_at, updated_at, revoked_at
                    FROM cp_virtual_key
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
                    UPDATE cp_virtual_key
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
                    UPDATE cp_virtual_key
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
                    FROM cp_key_policy
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
                        UPDATE cp_key_policy
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
                        INSERT INTO cp_key_policy (
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
                    FROM cp_key_policy WHERE key_id = %s
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
            metadata=payload.metadata,
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
            result = self._provider_from_row(row)
            # Sync to litellm config after updating provider
            self._sync_providers_to_litellm_config()
            return result

        data = payload.model_dump(exclude_none=True)
        updated = existing.model_copy(update={k: v for k, v in data.items() if k != "api_key"} | {"updated_at": datetime.now(UTC)})
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
            "policy": self._policy_seq,
            "v2policy": self._v2_key_policy_seq,
            "approval": self._approval_seq,
            "provider": self._provider_seq,
            "provider_probe": self._provider_probe_seq,
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

        with config_path.open("w", encoding="utf-8") as config_file:
            yaml.safe_dump(config, config_file, default_flow_style=False, sort_keys=False)

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

    def _build_litellm_runtime_artifacts(self) -> tuple[dict[str, Any], dict[str, str], int, str]:
        providers = sorted(self.list_providers(enabled=True), key=lambda item: item.id)
        model_entries: list[dict[str, Any]] = []
        env_vars: dict[str, str] = {}
        included_provider_count = 0

        for provider in providers:
            secret = self._get_provider_secret(provider.id)
            if not secret:
                continue

            included_provider_count += 1
            env_var_name = f"TEAM_AI_LITELLM_PROVIDER_{provider.id.upper()}_API_KEY"
            env_vars[env_var_name] = secret

            for model_id in self._provider_model_ids_from_state(provider):
                model_entries.append(
                    {
                        "model_name": self._build_provider_model_alias(provider, model_id),
                        "litellm_params": {
                            "model": self._build_litellm_model_ref(provider, model_id),
                            "api_base": provider.base_url,
                            "api_key": f"os.environ/{env_var_name}",
                        },
                    }
                )

        model_entries = sorted(model_entries, key=lambda entry: str(entry.get("model_name", "")))
        observability_backend, litellm_settings, observability_env_vars = self._build_observability_profile()
        env_vars.update(observability_env_vars)

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
            if normalized:
                return normalized
        return [self._default_provider_model_id(provider)]

    def _discover_provider_model_ids(self, provider: ProviderRecord, api_key: str) -> list[str]:
        endpoint = self._models_endpoint(provider.base_url)
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
    def _default_provider_model_id(provider: ProviderRecord) -> str:
        if provider.provider_type == "deepseek":
            return "deepseek-chat"
        if provider.preset_key:
            return provider.preset_key
        return "model"

    @staticmethod
    def _build_provider_model_alias(provider: ProviderRecord, model_id: str) -> str:
        prefix = provider.preset_key or provider.provider_type
        normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", model_id).strip("-").lower()
        if not normalized:
            normalized = "model"
        return f"{prefix}-{normalized}"

    @staticmethod
    def _build_litellm_model_ref(provider: ProviderRecord, model_id: str) -> str:
        model_value = model_id.strip()
        if provider.provider_type == "deepseek":
            return model_value if model_value.startswith("deepseek/") else f"deepseek/{model_value}"
        if provider.api_format == "openai":
            return model_value if model_value.startswith("openai/") else f"openai/{model_value}"
        if "/" in model_value:
            return model_value
        return f"{provider.provider_type}/{model_value}"

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
