from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..schemas import (
    PageResponse,
    V2KeyPolicyRecord,
    V2KeyPolicyUpsertRequest,
    V2OwnershipViewItem,
    V2VirtualKeyCreateRequest,
    V2VirtualKeyCreateResponse,
    V2VirtualKeyRecord,
    V2VirtualKeyRotateResponse,
)
from ..store import PlatformStore
from .dependencies import get_store, require_admin_token

router = APIRouter(prefix="/api/v1", tags=["control-plane-v2"], dependencies=[Depends(require_admin_token)])


@router.post("/keys", response_model=V2VirtualKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_virtual_key(
    payload: V2VirtualKeyCreateRequest,
    store: PlatformStore = Depends(get_store),
) -> V2VirtualKeyCreateResponse:
    record, key_secret = store.create_v2_virtual_key(payload)
    return V2VirtualKeyCreateResponse(key=record, key_secret=key_secret)


@router.get("/keys", response_model=PageResponse[V2VirtualKeyRecord])
def list_virtual_keys(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    team_id: str | None = None,
    owner_type: str | None = None,
    owner_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[V2VirtualKeyRecord]:
    records = store.list_v2_virtual_keys(
        team_id=team_id,
        owner_type=owner_type,
        owner_id=owner_id,
        status=status_filter,
    )
    paged = records[offset : offset + limit]
    return PageResponse[V2VirtualKeyRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.get("/governance/ownership", response_model=PageResponse[V2OwnershipViewItem])
def list_ownership_views(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    team_id: str | None = None,
    owner_type: str | None = None,
    owner_id: str | None = None,
    store: PlatformStore = Depends(get_store),
) -> PageResponse[V2OwnershipViewItem]:
    records = store.list_v2_ownership_views(
        team_id=team_id,
        owner_type=owner_type,
        owner_id=owner_id,
    )
    paged = records[offset : offset + limit]
    return PageResponse[V2OwnershipViewItem](items=paged, total=len(records), limit=limit, offset=offset)


@router.post("/keys/{key_id}/revoke", response_model=V2VirtualKeyRecord)
def revoke_virtual_key(
    key_id: str,
    store: PlatformStore = Depends(get_store),
) -> V2VirtualKeyRecord:
    record = store.revoke_v2_virtual_key(key_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    return record


@router.post("/keys/{key_id}/rotate", response_model=V2VirtualKeyRotateResponse)
def rotate_virtual_key(
    key_id: str,
    store: PlatformStore = Depends(get_store),
) -> V2VirtualKeyRotateResponse:
    result = store.rotate_v2_virtual_key(key_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    new_key, new_secret = result
    return V2VirtualKeyRotateResponse(old_key_id=key_id, new_key=new_key, new_key_secret=new_secret)


@router.put("/policies/keys/{key_id}", response_model=V2KeyPolicyRecord)
def upsert_key_policy(
    key_id: str,
    payload: V2KeyPolicyUpsertRequest,
    store: PlatformStore = Depends(get_store),
) -> V2KeyPolicyRecord:
    record = store.upsert_v2_key_policy(key_id, payload)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    return record


@router.get("/policies/keys/{key_id}", response_model=V2KeyPolicyRecord)
def get_key_policy(
    key_id: str,
    store: PlatformStore = Depends(get_store),
) -> V2KeyPolicyRecord:
    record = store.get_v2_key_policy(key_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return record
