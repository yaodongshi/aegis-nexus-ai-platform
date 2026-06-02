from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..harness import (
    HarnessPlanLockStore,
    InvalidPlanTransitionError,
    RuntimeAdapterRegistry,
)
from ..harness.schemas import (
    PlanCreateRequest,
    PlanRecord,
    RuntimeEventIngestRequest,
    RuntimeEventIngestResponse,
    RuntimeEventRecord,
    TraceEventsResponse,
)
from ..harness.trace_bridge import resolve_trace_id
from .dependencies import require_admin_token

router = APIRouter(
    prefix="/api/v1/harness",
    tags=["harness"],
    dependencies=[Depends(require_admin_token)],
)


def get_harness_store(request: Request) -> HarnessPlanLockStore:
    return request.app.state.harness_store


def get_runtime_registry(request: Request) -> RuntimeAdapterRegistry:
    return request.app.state.runtime_registry


@router.post("/plans", response_model=PlanRecord)
def create_plan(
    payload: PlanCreateRequest,
    request: Request,
    trace_id: str = Depends(resolve_trace_id),
    store: HarnessPlanLockStore = Depends(get_harness_store),
    runtime_registry: RuntimeAdapterRegistry = Depends(get_runtime_registry),
) -> PlanRecord:
    plan = store.create_plan(payload, trace_id=trace_id)
    adapter_name = (
        payload.metadata.get("runtime_adapter")
        if payload.metadata
        else None
    )
    adapter = runtime_registry.resolve(adapter_name)
    adapter.validate_plan(plan)
    request.state.trace_id = trace_id
    return plan


@router.get("/plans/{plan_id}", response_model=PlanRecord)
def get_plan(
    plan_id: str,
    store: HarnessPlanLockStore = Depends(get_harness_store),
) -> PlanRecord:
    plan = store.get_plan(plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )
    return plan


@router.post(
    "/plans/{plan_id}/events",
    response_model=RuntimeEventIngestResponse,
)
def ingest_runtime_event(
    plan_id: str,
    payload: RuntimeEventIngestRequest,
    request: Request,
    trace_id: str = Depends(resolve_trace_id),
    store: HarnessPlanLockStore = Depends(get_harness_store),
) -> RuntimeEventIngestResponse:
    try:
        plan, event = store.ingest_event(
            plan_id,
            trace_id=trace_id,
            payload=payload,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        ) from exc
    except InvalidPlanTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    request.state.trace_id = trace_id
    return RuntimeEventIngestResponse(plan=plan, event=event)


@router.get("/plans/{plan_id}/events", response_model=list[RuntimeEventRecord])
def list_plan_events(
    plan_id: str,
    store: HarnessPlanLockStore = Depends(get_harness_store),
) -> list[RuntimeEventRecord]:
    plan = store.get_plan(plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )
    return store.list_events_for_plan(plan_id)


@router.get("/traces/{trace_id}", response_model=TraceEventsResponse)
def get_trace(
    trace_id: str,
    store: HarnessPlanLockStore = Depends(get_harness_store),
) -> TraceEventsResponse:
    return store.get_trace(trace_id)
