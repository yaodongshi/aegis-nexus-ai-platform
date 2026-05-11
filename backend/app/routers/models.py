from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..schemas import ModelRegisterRequest, ModelRecord, ModelUpdateRequest, PageResponse
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=PageResponse[ModelRecord])
def list_models(
    provider: str | None = None,
    availability: str | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[ModelRecord]:
    records = store.list_models(
        provider=provider,
        availability=availability,
        limit=None,
        offset=0,
    )
    paged = records[offset : offset + limit]
    return PageResponse[ModelRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.post("", response_model=ModelRecord, status_code=status.HTTP_201_CREATED)
def register_model(payload: ModelRegisterRequest, store: PlatformStore = Depends(get_store)) -> ModelRecord:
    return store.register_model(payload)


@router.get("/{model_id}", response_model=ModelRecord)
def get_model(model_id: str, store: PlatformStore = Depends(get_store)) -> ModelRecord:
    record = store.get_model(model_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    return record


@router.patch("/{model_id}", response_model=ModelRecord)
def update_model(model_id: str, payload: ModelUpdateRequest, store: PlatformStore = Depends(get_store)) -> ModelRecord:
    record = store.update_model(model_id, payload)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    return record
