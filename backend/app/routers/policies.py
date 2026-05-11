from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..schemas import PageResponse, PolicyRecord, PolicyUpsertRequest
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("", response_model=PageResponse[PolicyRecord])
def list_policies(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[PolicyRecord]:
    records = store.list_policies()
    paged = records[offset : offset + limit]
    return PageResponse[PolicyRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.post("", response_model=PolicyRecord)
def upsert_policy(payload: PolicyUpsertRequest, store: PlatformStore = Depends(get_store)) -> PolicyRecord:
    return store.upsert_policy(payload)
