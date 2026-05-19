"""Audit log read-only view — data is written by feedbacks.append_audit_log()."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Header, Query

from ...feedback_schemas import AuditLogRecord
from .feedbacks import _AUDIT_LOGS
from .users import resolve_user_from_auth_header

router = APIRouter()


@router.get("/", response_model=List[AuditLogRecord])
def list_auditlogs(
    resource_type: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
):
    resolve_user_from_auth_header(authorization)
    items = list(_AUDIT_LOGS)
    if resource_type:
        items = [i for i in items if i["resource_type"] == resource_type]
    if actor_id:
        items = [i for i in items if i["actor_id"] == actor_id]
    return [AuditLogRecord(**i) for i in items]
