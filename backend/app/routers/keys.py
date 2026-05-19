from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..schemas import KeyIssueRequest, KeyIssueResponse, KeyRecord, PageResponse, KeyAuditLogResponse, KeyUsageStats
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/keys", tags=["keys"])


@router.get("", response_model=PageResponse[KeyRecord])
def list_keys(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user_id: str | None = None,
    project_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    q: str | None = None,
    store: PlatformStore = Depends(get_store),
) -> PageResponse[KeyRecord]:
    records = store.list_keys(
        user_id=user_id,
        project_id=project_id,
        status=status_filter,
        q=q,
    )
    paged = records[offset : offset + limit]
    return PageResponse[KeyRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.post("/issue", response_model=KeyIssueResponse, status_code=status.HTTP_201_CREATED)
def issue_key(payload: KeyIssueRequest, store: PlatformStore = Depends(get_store)) -> KeyIssueResponse:
    from datetime import datetime, timezone, timedelta
    # Handle expires_days convenience parameter
    if payload.expires_days and payload.expires_days > 0 and not payload.expire_at:
        now = datetime.now(timezone.utc)
        payload.expire_at = now + timedelta(days=payload.expires_days)
    _, response = store.issue_key(payload)
    return response


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_key(key_id: str, store: PlatformStore = Depends(get_store)) -> None:
    record = store.revoke_key(key_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")


# M1.3: Audit log and usage tracking endpoints
@router.get("/{key_id}/audit-log", response_model=KeyAuditLogResponse)
def get_key_audit_log(
    key_id: str,
    limit: int | None = Query(None, ge=1, le=1000),
    store: PlatformStore = Depends(get_store),
) -> KeyAuditLogResponse:
    """Get audit log entries for a virtual key.
    
    Returns the complete history of actions performed with this key
    (creation, use, revocation, etc.) in reverse chronological order.
    """
    if store.get_key_usage_stats(key_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    
    entries = store.get_key_audit_log(key_id, limit=limit)
    return KeyAuditLogResponse(
        key_id=key_id,
        entries=entries,
        total_entries=len(entries),
    )


@router.get("/{key_id}/usage", response_model=KeyUsageStats)
def get_key_usage(
    key_id: str,
    store: PlatformStore = Depends(get_store),
) -> KeyUsageStats:
    """Get usage statistics for a virtual key.
    
    Returns aggregate statistics including:
    - Total API calls made
    - Total tokens consumed
    - Breakdown by model
    - Time range of usage
    """
    stats = store.get_key_usage_stats(key_id)
    if stats is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    
    return KeyUsageStats(
        key_id=key_id,
        total_calls=stats.get("total_calls", 0),
        total_tokens_used=stats.get("total_tokens_used", 0),
        calls_by_model=stats.get("calls_by_model", {}),
        tokens_by_model=stats.get("tokens_by_model", {}),
        first_used_at=stats.get("first_used_at"),
        last_used_at=stats.get("last_used_at"),
        usage_by_hour=stats.get("usage_by_hour", {}),
    )
