from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from ..harness import (
    CapabilityAliasNotFoundError,
    HarnessPlanLockStore,
    InvalidPlanTransitionError,
    InvalidRolloutDecisionError,
    ReplayCheckpointNotFoundError,
    RuntimeAdapterRegistry,
)
from ..harness.schemas import (
    HarnessAlertEvaluationRequest,
    HarnessAlertEvaluationResponse,
    HarnessMetricsSnapshot,
    CapabilityAliasContractRecord,
    CapabilityAliasContractUpsertRequest,
    PlanCreateRequest,
    PlanRecord,
    ReplayTraceRequest,
    ReplayTraceResponse,
    RolloutDecisionRecord,
    RolloutDecisionRequest,
    RuntimeEventIngestRequest,
    RuntimeEventIngestResponse,
    RuntimeEventRecord,
    TraceEventsResponse,
)
from ..store import PlatformStore
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


def get_platform_store(request: Request) -> PlatformStore:
    return request.app.state.store


@router.post("/plans", response_model=PlanRecord)
def create_plan(
    payload: PlanCreateRequest,
    request: Request,
    trace_id: str = Depends(resolve_trace_id),
    store: HarnessPlanLockStore = Depends(get_harness_store),
    runtime_registry: RuntimeAdapterRegistry = Depends(get_runtime_registry),
) -> PlanRecord:
    contract = store.get_capability_contract(payload.capability_alias)
    metadata = dict(payload.metadata)
    strategy_id = payload.strategy_id
    adapter_name = metadata.get("runtime_adapter") if metadata else None
    if contract is not None:
        if strategy_id is None:
            strategy_id = contract.stable_strategy_id
        if not adapter_name:
            adapter_name = contract.runtime_adapter
            metadata["runtime_adapter"] = adapter_name
        metadata["capability_contract_version"] = contract.contract_version
        metadata["rollout"] = {
            "stable_strategy_id": contract.stable_strategy_id,
            "canary_strategy_id": contract.canary_strategy_id,
            "canary_traffic_percent": contract.canary_traffic_percent,
        }

    prepared_payload = payload.model_copy(
        update={
            "strategy_id": strategy_id,
            "metadata": metadata,
        }
    )

    plan = store.create_plan(prepared_payload, trace_id=trace_id)
    adapter = runtime_registry.resolve(adapter_name)
    adapter.validate_plan(plan)
    request.state.trace_id = trace_id
    return plan


@router.get(
    "/capabilities",
    response_model=list[CapabilityAliasContractRecord],
)
def list_capability_contracts(
    store: HarnessPlanLockStore = Depends(get_harness_store),
) -> list[CapabilityAliasContractRecord]:
    return store.list_capability_contracts()


@router.get("/metrics", response_model=HarnessMetricsSnapshot)
def get_harness_metrics(
    capability_alias: str | None = Query(default=None, max_length=128),
    store: HarnessPlanLockStore = Depends(get_harness_store),
) -> HarnessMetricsSnapshot:
    return store.get_metrics_snapshot(capability_alias)


@router.post(
    "/alerts/evaluate",
    response_model=HarnessAlertEvaluationResponse,
)
def evaluate_harness_alerts(
    payload: HarnessAlertEvaluationRequest,
    store: HarnessPlanLockStore = Depends(get_harness_store),
) -> HarnessAlertEvaluationResponse:
    return store.evaluate_alerts(payload)


@router.put(
    "/capabilities/{capability_alias}",
    response_model=CapabilityAliasContractRecord,
)
def upsert_capability_contract(
    capability_alias: str,
    payload: CapabilityAliasContractUpsertRequest,
    store: HarnessPlanLockStore = Depends(get_harness_store),
) -> CapabilityAliasContractRecord:
    return store.upsert_capability_contract(
        capability_alias=capability_alias,
        payload=payload,
    )


@router.get(
    "/capabilities/{capability_alias}",
    response_model=CapabilityAliasContractRecord,
)
def get_capability_contract(
    capability_alias: str,
    store: HarnessPlanLockStore = Depends(get_harness_store),
) -> CapabilityAliasContractRecord:
    contract = store.get_capability_contract(capability_alias)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capability alias contract not found",
        )
    return contract


@router.post(
    "/capabilities/{capability_alias}/rollout-decisions",
    response_model=RolloutDecisionRecord,
)
def create_rollout_decision(
    capability_alias: str,
    payload: RolloutDecisionRequest,
    request: Request,
    store: HarnessPlanLockStore = Depends(get_harness_store),
    platform_store: PlatformStore = Depends(get_platform_store),
) -> RolloutDecisionRecord:
    contract = store.get_capability_contract(capability_alias)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capability alias contract not found",
        )

    if store.requires_approval(contract.metadata, payload.action):
        approval_id = (payload.approval_id or "").strip()
        if not approval_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Approval required for this rollout transition",
            )

        approval = platform_store.get_approval(approval_id)
        if approval is None or approval.resource_id != capability_alias:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Approval not ready for this capability alias",
            )
        if approval.status != "approved":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Approval must be approved before rollout",
            )
    else:
        approval_id = (payload.approval_id or "").strip()
        approval = (
            platform_store.get_approval(approval_id) if approval_id else None
        )

    try:
        _, decision = store.record_rollout_decision(
            capability_alias=capability_alias,
            payload=payload,
            approval_status=(
                approval.status if approval is not None else None
            ),
        )
    except CapabilityAliasNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capability alias contract not found",
        ) from exc
    except InvalidRolloutDecisionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return decision


@router.get(
    "/capabilities/{capability_alias}/rollout-decisions",
    response_model=list[RolloutDecisionRecord],
)
def list_rollout_decisions(
    capability_alias: str,
    store: HarnessPlanLockStore = Depends(get_harness_store),
) -> list[RolloutDecisionRecord]:
    contract = store.get_capability_contract(capability_alias)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capability alias contract not found",
        )
    return store.list_rollout_decisions(capability_alias)


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


@router.post("/traces/{trace_id}/replay", response_model=ReplayTraceResponse)
def replay_trace(
    trace_id: str,
    payload: ReplayTraceRequest,
    store: HarnessPlanLockStore = Depends(get_harness_store),
) -> ReplayTraceResponse:
    try:
        return store.replay_trace(trace_id=trace_id, payload=payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trace or source plan not found",
        ) from exc
    except ReplayCheckpointNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
