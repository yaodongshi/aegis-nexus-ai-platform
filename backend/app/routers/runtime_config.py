from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..schemas import (
    ClientRuntimeConfigResponse,
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


@router.get("/client-config/{app}", response_model=ClientRuntimeConfigResponse)
def get_client_runtime_config(
    app: str,
    base_url: str | None = Query(default=None, description="Override gateway base URL (defaults to platform setting)."),
    api_key: str | None = Query(default=None, description="Override API key embedded in the rendered config."),
    store: PlatformStore = Depends(get_store),
) -> ClientRuntimeConfigResponse:
    """Render a CLI/IDE configuration block from the same canonical model
    registry used to generate the LiteLLM gateway. Currently supports: ``opencode``.
    """
    try:
        return store.build_client_runtime_config(app, gateway_base_url=base_url, api_key=api_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

