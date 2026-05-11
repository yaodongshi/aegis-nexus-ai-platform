from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..schemas import KeyIssueRequest, KeyIssueResponse, KeyRecord, PageResponse
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/keys", tags=["keys"])


@router.get("", response_model=PageResponse[KeyRecord])
def list_keys(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[KeyRecord]:
    records = store.list_keys()
    paged = records[offset : offset + limit]
    return PageResponse[KeyRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.post("/issue", response_model=KeyIssueResponse, status_code=status.HTTP_201_CREATED)
def issue_key(payload: KeyIssueRequest, store: PlatformStore = Depends(get_store)) -> KeyIssueResponse:
    _, response = store.issue_key(payload)
    return response


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_key(key_id: str, store: PlatformStore = Depends(get_store)) -> None:
    record = store.revoke_key(key_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
