from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..schemas import (
    ModelBatchRegisterRequest,
    ModelBatchRegisterResponse,
    ModelBatchDeleteRequest,
    ModelBatchDeleteResponse,
    ModelRegisterRequest,
    ModelRecord,
    ModelUpdateRequest,
    PageResponse,
)
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/models", tags=["models"])


# Specific alias routes (must come before generic {model_id} routes)
@router.get("/aliases", response_model=dict)
def list_aliases(
    provider: str | None = Query(None, description="Filter by provider (e.g., 'openai', 'anthropic')"),
    tier: str | None = Query(None, description="Filter by tier (e.g., 'pro', 'economy')"),
    store: PlatformStore = Depends(get_store),
) -> dict:
    """List all available model aliases.
    
    Query Parameters:
    - provider: Optional provider filter
    - tier: Optional tier filter
    
    Returns:
    - providers: List of available provider names
    - tiers: List of available tier names
    - aliases: List of all matching aliases
    """
    aliases = store.list_model_aliases(provider=provider, tier=tier)
    providers = store.get_alias_providers()
    tiers = store.get_alias_tiers()
    return {
        "providers": providers,
        "tiers": tiers,
        "aliases": aliases,
        "total": len(aliases),
    }


@router.get("/aliases/{alias}", response_model=dict)
def get_alias(alias: str, store: PlatformStore = Depends(get_store)) -> dict:
    """Get detailed information about a specific model alias.
    
    Args:
        alias: Model alias (e.g., 'gpt4o-pro-128k')
        
    Returns:
        Detailed alias information including real model ID, provider, tier, etc.
    """
    alias_info = store.get_model_by_alias(alias)
    if alias_info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alias '{alias}' not found")
    return alias_info


# Generic model routes
@router.get("", response_model=PageResponse[ModelRecord])
def list_models(
    provider: str | None = None,
    provider_id: str | None = None,
    availability: str | None = None,
    alias: str | None = Query(None, description="Optional: filter by model alias instead of model ID"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[ModelRecord]:
    # If alias is provided, try to resolve it to a real model ID
    if alias:
        alias_info = store.get_model_by_alias(alias)
        if alias_info is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alias '{alias}' not found")
        # Return a mock ModelRecord for the alias
        return PageResponse[ModelRecord](
            items=[
                ModelRecord(
                    id=alias,
                    provider=alias_info["provider"],
                    name=alias_info["description"],
                    endpoint="",
                    context_window=alias_info["context_window"],
                    cost_tier="high" if alias_info["tier"] == "pro" else ("medium" if alias_info["tier"] == "standard" else "low"),
                    availability="active",
                    tags=alias_info.get("supported_capabilities", []),
                    labels={"tier": alias_info["tier"], "real_model_id": alias_info["real_model_id"]},
                    quota=None,
                    created_at=None,
                    updated_at=None,
                )
            ],
            total=1,
            limit=limit,
            offset=offset,
        )
    
    records = store.list_models(
        provider=provider,
        provider_id=provider_id,
        availability=availability,
        limit=None,
        offset=0,
    )
    paged = records[offset : offset + limit]
    return PageResponse[ModelRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.post("", response_model=ModelRecord, status_code=status.HTTP_201_CREATED)
def register_model(payload: ModelRegisterRequest, store: PlatformStore = Depends(get_store)) -> ModelRecord:
    return store.register_model(payload)


@router.post("/batch-register", response_model=ModelBatchRegisterResponse)
def batch_register_models(
    payload: ModelBatchRegisterRequest,
    store: PlatformStore = Depends(get_store),
) -> ModelBatchRegisterResponse:
    return store.batch_register_models(payload)


@router.post("/batch-delete", response_model=ModelBatchDeleteResponse)
def batch_delete_models(
    payload: ModelBatchDeleteRequest,
    store: PlatformStore = Depends(get_store),
) -> ModelBatchDeleteResponse:
    return store.batch_delete_models(payload)


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


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(model_id: str, store: PlatformStore = Depends(get_store)) -> None:
    if not store.delete_model(model_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
