from __future__ import annotations

from datetime import UTC, datetime
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query, status

from ...feedback_schemas import AuditLogRecord, FeedbackCreateRequest, FeedbackRecord
from .users import resolve_user_from_auth_header

router = APIRouter()

_FEEDBACKS: dict[str, dict] = {}
_AUDIT_LOGS: list[dict] = []


# ── Public helpers ────────────────────────────────────────────────────────────

def append_audit_log(
    actor_id: str,
    actor_name: str,
    action: str,
    resource_type: str,
    resource_id: str,
    detail: str,
) -> None:
    """Append an immutable audit log entry. Called by other modules."""
    _AUDIT_LOGS.append({
        "id": f"aud_{uuid4().hex[:10]}",
        "actor_id": actor_id,
        "actor_name": actor_name,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "detail": detail,
        "created_at": datetime.now(UTC),
    })


# ── Feedback routes ───────────────────────────────────────────────────────────

@router.post("/", response_model=FeedbackRecord, status_code=status.HTTP_201_CREATED)
def create_feedback(payload: FeedbackCreateRequest, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    now = datetime.now(UTC)
    fb_id = f"fb_{uuid4().hex[:10]}"
    record = {
        "id": fb_id,
        "resource_type": payload.resource_type,
        "resource_id": payload.resource_id,
        "content": payload.content.strip(),
        "rating": payload.rating,
        "created_by": current["id"],
        "created_at": now,
    }
    _FEEDBACKS[fb_id] = record
    append_audit_log(
        actor_id=current["id"],
        actor_name=current.get("username", ""),
        action="create",
        resource_type="feedback",
        resource_id=fb_id,
        detail=f"Feedback on {payload.resource_type}/{payload.resource_id}",
    )
    return FeedbackRecord(**record)


@router.get("/", response_model=List[FeedbackRecord])
def list_feedbacks(
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
):
    resolve_user_from_auth_header(authorization)
    items = list(_FEEDBACKS.values())
    if resource_type:
        items = [i for i in items if i["resource_type"] == resource_type]
    if resource_id:
        items = [i for i in items if i["resource_id"] == resource_id]
    return [FeedbackRecord(**i) for i in items]


@router.get("/{feedback_id}", response_model=FeedbackRecord)
def get_feedback(feedback_id: str, authorization: str | None = Header(default=None)):
    resolve_user_from_auth_header(authorization)
    item = _FEEDBACKS.get(feedback_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    return FeedbackRecord(**item)


# ── Audit log routes (read-only) ──────────────────────────────────────────────

@router.get("/audit/logs", response_model=List[AuditLogRecord])
def list_audit_logs(
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
