from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..schemas import PageResponse, SessionCreateRequest, SessionRecord, SessionUpdateRequest
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=PageResponse[SessionRecord])
def list_sessions(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[SessionRecord]:
    records = store.list_sessions()
    paged = records[offset : offset + limit]
    return PageResponse[SessionRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.get("/{session_id}", response_model=SessionRecord)
def get_session(session_id: str, store: PlatformStore = Depends(get_store)) -> SessionRecord:
    record = store.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return record


@router.post("", response_model=SessionRecord, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreateRequest, store: PlatformStore = Depends(get_store)) -> SessionRecord:
    return store.create_session(payload)


@router.patch("/{session_id}", response_model=SessionRecord)
def update_session(session_id: str, payload: SessionUpdateRequest, store: PlatformStore = Depends(get_store)) -> SessionRecord:
    record = store.update_session(session_id, payload)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return record
