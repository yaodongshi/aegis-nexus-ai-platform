from __future__ import annotations

from collections import defaultdict
from threading import Lock
from uuid import uuid4

from .schemas import (
    PlanCreateRequest,
    PlanRecord,
    PlanState,
    RuntimeEventIngestRequest,
    RuntimeEventRecord,
    RuntimeEventType,
    TraceEventsResponse,
    utcnow,
)


STATE_TRANSITIONS: dict[PlanState, set[PlanState]] = {
    PlanState.CREATED: {PlanState.VALIDATED, PlanState.FAILED},
    PlanState.VALIDATED: {PlanState.READY, PlanState.FAILED},
    PlanState.READY: {PlanState.RUNNING, PlanState.FAILED},
    PlanState.RUNNING: {
        PlanState.BLOCKED,
        PlanState.FAILED,
        PlanState.COMPLETED,
        PlanState.ROLLED_BACK,
    },
    PlanState.BLOCKED: {
        PlanState.RUNNING,
        PlanState.FAILED,
        PlanState.ROLLED_BACK,
    },
    PlanState.FAILED: {PlanState.ROLLED_BACK},
    PlanState.COMPLETED: set(),
    PlanState.ROLLED_BACK: set(),
}


EVENT_TO_STATE: dict[RuntimeEventType, PlanState] = {
    RuntimeEventType.VALIDATE: PlanState.VALIDATED,
    RuntimeEventType.PREPARE: PlanState.READY,
    RuntimeEventType.START: PlanState.RUNNING,
    RuntimeEventType.BLOCK: PlanState.BLOCKED,
    RuntimeEventType.FAIL: PlanState.FAILED,
    RuntimeEventType.COMPLETE: PlanState.COMPLETED,
    RuntimeEventType.ROLLBACK: PlanState.ROLLED_BACK,
}


class InvalidPlanTransitionError(ValueError):
    pass


class HarnessPlanLockStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._plans: dict[str, PlanRecord] = {}
        self._events: dict[str, RuntimeEventRecord] = {}
        self._events_by_plan: dict[str, list[str]] = defaultdict(list)
        self._plans_by_trace: dict[str, list[str]] = defaultdict(list)
        self._events_by_trace: dict[str, list[str]] = defaultdict(list)

    def create_plan(
        self,
        payload: PlanCreateRequest,
        trace_id: str,
    ) -> PlanRecord:
        now = utcnow()
        plan = PlanRecord(
            plan_id=f"plan-{uuid4().hex}",
            trace_id=trace_id,
            capability_alias=payload.capability_alias,
            strategy_id=payload.strategy_id,
            state=PlanState.CREATED,
            metadata=payload.metadata,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._plans[plan.plan_id] = plan
            self._plans_by_trace[trace_id].append(plan.plan_id)
        return plan

    def get_plan(self, plan_id: str) -> PlanRecord | None:
        with self._lock:
            return self._plans.get(plan_id)

    def ingest_event(
        self,
        plan_id: str,
        trace_id: str,
        payload: RuntimeEventIngestRequest,
    ) -> tuple[PlanRecord, RuntimeEventRecord]:
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                raise KeyError(plan_id)
            if plan.trace_id != trace_id:
                # Keep trace integrity strict for replay/audit.
                raise InvalidPlanTransitionError("trace_id mismatch for plan")

            target_state = EVENT_TO_STATE[payload.event_type]
            if target_state not in STATE_TRANSITIONS[plan.state]:
                raise InvalidPlanTransitionError(
                    f"invalid transition: {plan.state} -> {target_state}"
                )

            now = utcnow()
            plan = plan.model_copy(
                update={"state": target_state, "updated_at": now}
            )
            self._plans[plan_id] = plan

            event = RuntimeEventRecord(
                event_id=f"evt-{uuid4().hex}",
                plan_id=plan_id,
                trace_id=trace_id,
                event_type=payload.event_type,
                source=payload.source,
                payload=payload.payload,
                occurred_at=now,
            )
            self._events[event.event_id] = event
            self._events_by_plan[plan_id].append(event.event_id)
            self._events_by_trace[trace_id].append(event.event_id)
            return plan, event

    def list_events_for_plan(self, plan_id: str) -> list[RuntimeEventRecord]:
        with self._lock:
            event_ids = self._events_by_plan.get(plan_id, [])
            return [self._events[event_id] for event_id in event_ids]

    def get_trace(self, trace_id: str) -> TraceEventsResponse:
        with self._lock:
            plan_ids = self._plans_by_trace.get(trace_id, [])
            event_ids = self._events_by_trace.get(trace_id, [])
            return TraceEventsResponse(
                trace_id=trace_id,
                plans=[self._plans[plan_id] for plan_id in plan_ids],
                events=[self._events[event_id] for event_id in event_ids],
            )
