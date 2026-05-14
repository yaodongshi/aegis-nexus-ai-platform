from __future__ import annotations

from fastapi import APIRouter, Depends

from ..schemas import (
    RuntimeConfigApplyRequest,
    RuntimeConfigApplyResponse,
    RuntimeConfigPreviewResponse,
)
from ..store import PlatformStore
from .dependencies import get_store, require_admin_token

router = APIRouter(prefix="/api/v1/runtime", tags=["runtime-config"], dependencies=[Depends(require_admin_token)])


@router.get("/litellm-config", response_model=RuntimeConfigPreviewResponse)
def preview_litellm_config(store: PlatformStore = Depends(get_store)) -> RuntimeConfigPreviewResponse:
    return store.preview_litellm_runtime_config()


@router.post("/litellm-config/apply", response_model=RuntimeConfigApplyResponse)
def apply_litellm_config(
    payload: RuntimeConfigApplyRequest,
    store: PlatformStore = Depends(get_store),
) -> RuntimeConfigApplyResponse:
    return store.apply_litellm_runtime_config(output_dir=payload.output_dir)
