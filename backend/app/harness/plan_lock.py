from __future__ import annotations

from collections import defaultdict
from threading import Lock
from uuid import uuid4

from .schemas import (
    CapabilityAliasContractRecord,
    CapabilityAliasContractUpsertRequest,
    PlanCreateRequest,
    PlanRecord,
    PlanState,
    RolloutAction,
    RolloutDecisionRecord,
    RolloutDecisionRequest,
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


class CapabilityAliasNotFoundError(KeyError):
    pass


class InvalidRolloutDecisionError(ValueError):
    pass


class HarnessPlanLockStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._plans: dict[str, PlanRecord] = {}
        self._events: dict[str, RuntimeEventRecord] = {}
        self._events_by_plan: dict[str, list[str]] = defaultdict(list)
        self._plans_by_trace: dict[str, list[str]] = defaultdict(list)
        self._events_by_trace: dict[str, list[str]] = defaultdict(list)
        self._capability_contracts: dict[
            str,
            CapabilityAliasContractRecord,
        ] = {}
        self._rollout_decisions: dict[str, RolloutDecisionRecord] = {}
        self._decisions_by_alias: dict[str, list[str]] = defaultdict(list)

    def upsert_capability_contract(
        self,
        capability_alias: str,
        payload: CapabilityAliasContractUpsertRequest,
    ) -> CapabilityAliasContractRecord:
        now = utcnow()
        with self._lock:
            existing = self._capability_contracts.get(capability_alias)
            created_at = existing.created_at if existing else now
            record = CapabilityAliasContractRecord(
                capability_alias=capability_alias,
                contract_version=payload.contract_version,
                runtime_adapter=payload.runtime_adapter,
                stable_strategy_id=payload.stable_strategy_id,
                canary_strategy_id=payload.canary_strategy_id,
                canary_traffic_percent=payload.canary_traffic_percent,
                metadata=payload.metadata,
                created_at=created_at,
                updated_at=now,
            )
            self._capability_contracts[capability_alias] = record
            return record

    def get_capability_contract(
        self,
        capability_alias: str,
    ) -> CapabilityAliasContractRecord | None:
        with self._lock:
            return self._capability_contracts.get(capability_alias)

    def list_capability_contracts(self) -> list[CapabilityAliasContractRecord]:
        with self._lock:
            return list(self._capability_contracts.values())

    def record_rollout_decision(
        self,
        capability_alias: str,
        payload: RolloutDecisionRequest,
    ) -> tuple[CapabilityAliasContractRecord, RolloutDecisionRecord]:
        with self._lock:
            record = self._capability_contracts.get(capability_alias)
            if record is None:
                raise CapabilityAliasNotFoundError(capability_alias)

            stable_before = record.stable_strategy_id
            canary_before = record.canary_strategy_id
            canary_after = canary_before
            stable_after = stable_before
            canary_traffic_after = record.canary_traffic_percent

            if payload.action is RolloutAction.CANARY:
                candidate = payload.candidate_strategy_id
                if not candidate:
                    raise InvalidRolloutDecisionError(
                        "candidate_strategy_id is required for canary",
                    )
                canary_after = candidate
                if payload.canary_traffic_percent is None:
                    canary_traffic_after = max(1, canary_traffic_after)
                else:
                    canary_traffic_after = payload.canary_traffic_percent

            if payload.action is RolloutAction.PROMOTE:
                candidate = payload.candidate_strategy_id or canary_before
                if not candidate:
                    raise InvalidRolloutDecisionError(
                        "candidate_strategy_id is required for promote",
                    )
                stable_after = candidate
                canary_after = None
                canary_traffic_after = 0

            if payload.action is RolloutAction.DEMOTE:
                candidate = payload.candidate_strategy_id or canary_before
                if not candidate:
                    raise InvalidRolloutDecisionError(
                        "candidate_strategy_id is required for demote",
                    )
                if canary_before and canary_before != candidate:
                    raise InvalidRolloutDecisionError(
                        "candidate_strategy_id does not match current canary",
                    )
                canary_after = None
                canary_traffic_after = 0

            if payload.action is RolloutAction.ROLLBACK:
                canary_after = None
                canary_traffic_after = 0

            now = utcnow()
            updated_record = record.model_copy(
                update={
                    "stable_strategy_id": stable_after,
                    "canary_strategy_id": canary_after,
                    "canary_traffic_percent": canary_traffic_after,
                    "updated_at": now,
                }
            )
            self._capability_contracts[capability_alias] = updated_record

            decision = RolloutDecisionRecord(
                decision_id=f"rdec-{uuid4().hex}",
                capability_alias=capability_alias,
                action=payload.action,
                stable_strategy_before=stable_before,
                canary_strategy_before=canary_before,
                stable_strategy_after=stable_after,
                canary_strategy_after=canary_after,
                canary_traffic_percent_after=canary_traffic_after,
                baseline_metrics=payload.baseline_metrics,
                candidate_metrics=payload.candidate_metrics,
                thresholds=payload.thresholds,
                actor=payload.actor,
                rationale=payload.rationale,
                metadata=payload.metadata,
                decided_at=now,
            )
            self._rollout_decisions[decision.decision_id] = decision
            self._decisions_by_alias[capability_alias].append(
                decision.decision_id
            )
            return updated_record, decision

    def list_rollout_decisions(
        self,
        capability_alias: str,
    ) -> list[RolloutDecisionRecord]:
        with self._lock:
            decision_ids = self._decisions_by_alias.get(capability_alias, [])
            return [self._rollout_decisions[item] for item in decision_ids]

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
