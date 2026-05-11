from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas import ModelRegisterRequest, ModelRecord, ModelUpdateRequest
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=list[ModelRecord])
def list_models(store: PlatformStore = Depends(get_store)) -> list[ModelRecord]:
    return store.list_models()


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
