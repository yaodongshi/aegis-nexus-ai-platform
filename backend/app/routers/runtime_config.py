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

QUERY_BASE_URL_DESC = (
    "Override gateway base URL "
    "(defaults to platform setting)."
)
QUERY_API_KEY_DESC = "Override API key embedded in the rendered config."

router = APIRouter(
    prefix="/api/v1/runtime",
    tags=["runtime-config"],
    dependencies=[Depends(require_admin_token)],
)


def _build_client_config_response(
    app: str,
    *,
    base_url: str | None,
    api_key: str | None,
    store: PlatformStore,
) -> ClientRuntimeConfigResponse:
    try:
        return store.build_client_runtime_config(
            app,
            gateway_base_url=base_url,
            api_key=api_key,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/litellm-config", response_model=RuntimeConfigPreviewResponse)
def preview_litellm_config(
    store: PlatformStore = Depends(get_store),
) -> RuntimeConfigPreviewResponse:
    return store.preview_litellm_runtime_config()


@router.post(
    "/litellm-config/apply",
    response_model=RuntimeConfigApplyResponse,
)
def apply_litellm_config(
    payload: RuntimeConfigApplyRequest,
    store: PlatformStore = Depends(get_store),
) -> RuntimeConfigApplyResponse:
    return store.apply_litellm_runtime_config(output_dir=payload.output_dir)


@router.get("/client-config/cursor", response_model=ClientRuntimeConfigResponse)
def get_cursor_client_config(
    base_url: str | None = Query(default=None, description=QUERY_BASE_URL_DESC),
    api_key: str | None = Query(default=None, description=QUERY_API_KEY_DESC),
    store: PlatformStore = Depends(get_store),
) -> ClientRuntimeConfigResponse:
    return _build_client_config_response(
        "cursor",
        base_url=base_url,
        api_key=api_key,
        store=store,
    )


@router.get("/client-config/claude-code", response_model=ClientRuntimeConfigResponse)
def get_claude_code_client_config(
    base_url: str | None = Query(default=None, description=QUERY_BASE_URL_DESC),
    api_key: str | None = Query(default=None, description=QUERY_API_KEY_DESC),
    store: PlatformStore = Depends(get_store),
) -> ClientRuntimeConfigResponse:
    return _build_client_config_response(
        "claude-code",
        base_url=base_url,
        api_key=api_key,
        store=store,
    )


@router.get("/client-config/continue", response_model=ClientRuntimeConfigResponse)
def get_continue_client_config(
    base_url: str | None = Query(default=None, description=QUERY_BASE_URL_DESC),
    api_key: str | None = Query(default=None, description=QUERY_API_KEY_DESC),
    store: PlatformStore = Depends(get_store),
) -> ClientRuntimeConfigResponse:
    return _build_client_config_response(
        "continue",
        base_url=base_url,
        api_key=api_key,
        store=store,
    )


@router.get("/client-config/{app}", response_model=ClientRuntimeConfigResponse)
def get_client_runtime_config(
    app: str,
    base_url: str | None = Query(default=None, description=QUERY_BASE_URL_DESC),
    api_key: str | None = Query(default=None, description=QUERY_API_KEY_DESC),
    store: PlatformStore = Depends(get_store),
) -> ClientRuntimeConfigResponse:
    """Render a CLI/IDE configuration block from the same canonical model
    registry used to generate the LiteLLM gateway.
    """
    return _build_client_config_response(
        app,
        base_url=base_url,
        api_key=api_key,
        store=store,
    )

