from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas import KeyIssueRequest, KeyIssueResponse, KeyRecord
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/keys", tags=["keys"])


@router.get("", response_model=list[KeyRecord])
def list_keys(store: PlatformStore = Depends(get_store)) -> list[KeyRecord]:
    return store.list_keys()


@router.post("/issue", response_model=KeyIssueResponse, status_code=status.HTTP_201_CREATED)
def issue_key(payload: KeyIssueRequest, store: PlatformStore = Depends(get_store)) -> KeyIssueResponse:
    _, response = store.issue_key(payload)
    return response


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_key(key_id: str, store: PlatformStore = Depends(get_store)) -> None:
    record = store.revoke_key(key_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
