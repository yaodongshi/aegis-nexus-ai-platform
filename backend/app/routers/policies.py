from __future__ import annotations

from fastapi import APIRouter, Depends

from ..schemas import PolicyRecord, PolicyUpsertRequest
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("", response_model=list[PolicyRecord])
def list_policies(store: PlatformStore = Depends(get_store)) -> list[PolicyRecord]:
    return store.list_policies()


@router.post("", response_model=PolicyRecord)
def upsert_policy(payload: PolicyUpsertRequest, store: PlatformStore = Depends(get_store)) -> PolicyRecord:
    return store.upsert_policy(payload)
