from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas import ApprovalRecord, ApprovalSubmitRequest
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalRecord])
def list_approvals(store: PlatformStore = Depends(get_store)) -> list[ApprovalRecord]:
    return store.list_approvals()


@router.post("/submit", response_model=ApprovalRecord, status_code=status.HTTP_201_CREATED)
def submit_approval(payload: ApprovalSubmitRequest, store: PlatformStore = Depends(get_store)) -> ApprovalRecord:
    return store.submit_approval(payload)


@router.get("/{approval_id}", response_model=ApprovalRecord)
def get_approval(approval_id: str, store: PlatformStore = Depends(get_store)) -> ApprovalRecord:
    record = store.get_approval(approval_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found")
    return record
