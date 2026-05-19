from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from ..schemas import ApprovalRecord, ApprovalSubmitRequest, PageResponse
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("", response_model=PageResponse[ApprovalRecord])
def list_approvals(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[ApprovalRecord]:
    records = store.list_approvals()
    paged = records[offset : offset + limit]
    return PageResponse[ApprovalRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.post("/submit", response_model=ApprovalRecord, status_code=status.HTTP_201_CREATED)
def submit_approval(payload: ApprovalSubmitRequest, store: PlatformStore = Depends(get_store)) -> ApprovalRecord:
    return store.submit_approval(payload)


@router.get("/{approval_id}", response_model=ApprovalRecord)
def get_approval(approval_id: str, store: PlatformStore = Depends(get_store)) -> ApprovalRecord:
    record = store.get_approval(approval_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    return record


@router.post("/{approval_id}/approve", response_model=ApprovalRecord)
def approve_approval(
    approval_id: str,
    reason: str | None = Body(default=None, embed=True),
    approver_id: str = Body(default="admin", embed=True),
    store: PlatformStore = Depends(get_store),
) -> ApprovalRecord:
    record = store.approve_approval(approval_id, approver_id=approver_id, reason=reason)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found or already processed",
        )
    return record


@router.post("/{approval_id}/reject", response_model=ApprovalRecord)
def reject_approval(
    approval_id: str,
    reason: str | None = Body(default=None, embed=True),
    approver_id: str = Body(default="admin", embed=True),
    store: PlatformStore = Depends(get_store),
) -> ApprovalRecord:
    record = store.reject_approval(approval_id, approver_id=approver_id, reason=reason)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found or already processed",
        )
    return record
