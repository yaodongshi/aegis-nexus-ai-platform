from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..provider_presets import PRESET_PROVIDERS
from ..schemas import (
    PageResponse,
    ProviderBatchProbeRequest,
    ProviderBatchProbeResponse,
    ProviderCreateRequest,
    ProviderProbeLogRecord,
    ProviderModelDiscoveryResponse,
    ProviderProbeRequest,
    ProviderProbeResponse,
    ProviderPresetRecord,
    ProviderRecord,
    ProviderSyncRequest,
    ProviderUpdateRequest,
)
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("/presets", response_model=list[ProviderPresetRecord])
def list_provider_presets() -> list[ProviderPresetRecord]:
    return PRESET_PROVIDERS


@router.get("", response_model=PageResponse[ProviderRecord])
def list_providers(
    scope: str | None = None,
    app: str | None = None,
    enabled: bool | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[ProviderRecord]:
    records = store.list_providers(scope=scope, app=app, enabled=enabled)
    paged = records[offset : offset + limit]
    return PageResponse[ProviderRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.post("", response_model=ProviderRecord, status_code=status.HTTP_201_CREATED)
def create_provider(payload: ProviderCreateRequest, store: PlatformStore = Depends(get_store)) -> ProviderRecord:
    return store.create_provider(payload)


@router.get("/{provider_id}", response_model=ProviderRecord)
def get_provider(provider_id: str, store: PlatformStore = Depends(get_store)) -> ProviderRecord:
    record = store.get_provider(provider_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return record


@router.patch("/{provider_id}", response_model=ProviderRecord)
def update_provider(
    provider_id: str,
    payload: ProviderUpdateRequest,
    store: PlatformStore = Depends(get_store),
) -> ProviderRecord:
    record = store.update_provider(provider_id, payload)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return record


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(provider_id: str, store: PlatformStore = Depends(get_store)) -> None:
    if not store.delete_provider(provider_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")


@router.post("/{provider_id}/sync", response_model=ProviderRecord)
def sync_provider(
    provider_id: str,
    payload: ProviderSyncRequest,
    store: PlatformStore = Depends(get_store),
) -> ProviderRecord:
    record = store.sync_provider(provider_id, payload)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return record


@router.post("/{provider_id}/discover-models", response_model=ProviderModelDiscoveryResponse)
def discover_provider_models(
    provider_id: str,
    store: PlatformStore = Depends(get_store),
) -> ProviderModelDiscoveryResponse:
    try:
        return store.discover_provider_models(provider_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch provider models") from exc


@router.post("/{provider_id}/probe", response_model=ProviderProbeResponse)
def probe_provider_endpoints(
    provider_id: str,
    payload: ProviderProbeRequest,
    store: PlatformStore = Depends(get_store),
) -> ProviderProbeResponse:
    try:
        return store.probe_provider_endpoints(provider_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to probe provider endpoints") from exc


@router.get("/{provider_id}/probe-history", response_model=list[ProviderProbeLogRecord])
def list_provider_probe_history(
    provider_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    store: PlatformStore = Depends(get_store),
) -> list[ProviderProbeLogRecord]:
    try:
        return store.list_provider_probe_logs(provider_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/probe-all", response_model=ProviderBatchProbeResponse)
def probe_all_providers(
    payload: ProviderBatchProbeRequest,
    store: PlatformStore = Depends(get_store),
) -> ProviderBatchProbeResponse:
    return store.batch_probe_providers(payload)
