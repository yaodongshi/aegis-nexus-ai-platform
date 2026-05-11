from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas import SessionCreateRequest, SessionRecord, SessionUpdateRequest
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionRecord])
def list_sessions(store: PlatformStore = Depends(get_store)) -> list[SessionRecord]:
    return store.list_sessions()


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
