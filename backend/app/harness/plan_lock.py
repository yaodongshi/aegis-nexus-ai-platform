from __future__ import annotations

from collections import defaultdict
import math
from threading import Lock
from typing import Any
from uuid import uuid4

from .schemas import (
    CapabilityAliasContractRecord,
    CapabilityAliasContractUpsertRequest,
    HarnessAlert,
    HarnessAlertEvaluationRequest,
    HarnessAlertEvaluationResponse,
    HarnessMetricsSnapshot,
    PlanCreateRequest,
    PlanRecord,
    PlanState,
    ReplayTraceRequest,
    ReplayTraceResponse,
    RolloutAction,
    RolloutDecisionRecord,
    RolloutDecisionRequest,
    RuntimeEventIngestRequest,
    RuntimeEventRecord,
    RuntimeEventType,
    TraceEventsResponse,
    new_trace_id,
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


class ApprovalGateRequiredError(PermissionError):
    pass


class ApprovalNotReadyError(PermissionError):
    pass


class ReplayCheckpointNotFoundError(ValueError):
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
        approval_status: str | None = None,
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
                approval_id=payload.approval_id,
                approval_status=approval_status,
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

    @staticmethod
    def requires_approval(
        contract_metadata: dict[str, Any],
        action: RolloutAction,
    ) -> bool:
        required_actions = contract_metadata.get("approval_required_actions")
        if isinstance(required_actions, list) and (
            action.value in required_actions
        ):
            return True

        if contract_metadata.get("requires_approval") is True:
            return action in {RolloutAction.PROMOTE, RolloutAction.ROLLBACK}

        risk_level = str(contract_metadata.get("risk_level") or "").lower()
        if risk_level in {"p0", "p1", "high"}:
            return action in {RolloutAction.PROMOTE, RolloutAction.ROLLBACK}

        return False

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

    def replay_trace(
        self,
        trace_id: str,
        payload: ReplayTraceRequest,
    ) -> ReplayTraceResponse:
        with self._lock:
            plan_ids = list(self._plans_by_trace.get(trace_id, []))
            if not plan_ids:
                raise KeyError(trace_id)

            source_plan = self._resolve_source_plan(
                plan_ids,
                payload.source_plan_id,
            )
            source_event_ids = self._events_by_plan.get(
                source_plan.plan_id,
                [],
            )
            source_events = [self._events[item] for item in source_event_ids]

        stable_checkpoint = self._resolve_stable_checkpoint(source_events)
        if stable_checkpoint is None:
            raise ReplayCheckpointNotFoundError(
                "no stable checkpoint event found for replay",
            )

        replay_trace_id = new_trace_id()
        replay_metadata = dict(source_plan.metadata)
        replay_metadata["replay"] = {
            "source_trace_id": trace_id,
            "source_plan_id": source_plan.plan_id,
            "checkpoint_event_id": stable_checkpoint.event_id,
            "actor": payload.actor,
        }
        replay_plan_payload = PlanCreateRequest(
            capability_alias=source_plan.capability_alias,
            strategy_id=source_plan.strategy_id,
            metadata=replay_metadata,
        )
        replay_plan = self.create_plan(
            replay_plan_payload,
            trace_id=replay_trace_id,
        )

        replay_count = 0
        checkpoint_chain = self._checkpoint_event_chain(stable_checkpoint)
        replay_checkpoint_event = stable_checkpoint
        for event_type in checkpoint_chain:
            replay_count += 1
            replay_payload = RuntimeEventIngestRequest(
                event_type=event_type,
                source="replay",
                payload={
                    "source_trace_id": trace_id,
                    "source_plan_id": source_plan.plan_id,
                    "checkpoint_event_id": stable_checkpoint.event_id,
                },
            )
            replay_plan, replay_checkpoint_event = self.ingest_event(
                replay_plan.plan_id,
                trace_id=replay_trace_id,
                payload=replay_payload,
            )

        return ReplayTraceResponse(
            replay_plan=replay_plan,
            replay_checkpoint_event=replay_checkpoint_event,
            replayed_event_count=replay_count,
        )

    def get_metrics_snapshot(
        self,
        capability_alias: str | None = None,
    ) -> HarnessMetricsSnapshot:
        with self._lock:
            plans = [
                plan
                for plan in self._plans.values()
                if capability_alias is None
                or plan.capability_alias == capability_alias
            ]
            plan_ids = {plan.plan_id for plan in plans}
            events = [
                event
                for event in self._events.values()
                if event.plan_id in plan_ids
            ]

        terminal_states = {
            PlanState.COMPLETED,
            PlanState.FAILED,
            PlanState.ROLLED_BACK,
        }
        terminal_total = sum(
            1 for plan in plans if plan.state in terminal_states
        )
        completed_total = sum(
            1 for plan in plans if plan.state is PlanState.COMPLETED
        )
        failed_total = sum(
            1 for plan in plans if plan.state is PlanState.FAILED
        )
        rolled_back_total = sum(
            1 for plan in plans if plan.state is PlanState.ROLLED_BACK
        )

        success_rate = (
            completed_total / terminal_total if terminal_total > 0 else 0.0
        )
        rollback_rate = (
            rolled_back_total / terminal_total if terminal_total > 0 else 0.0
        )

        latency_values = [
            value
            for value in (
                self._as_float(event.payload.get("latency_ms"))
                for event in events
            )
            if value is not None
        ]
        avg_latency_ms = (
            sum(latency_values) / len(latency_values)
            if latency_values
            else None
        )
        p95_latency_ms = (
            self._percentile(latency_values, 0.95)
            if latency_values
            else None
        )

        total_cost_usd = sum(
            value
            for value in (
                self._as_float(event.payload.get("cost_usd"))
                for event in events
            )
            if value is not None
        )

        return HarnessMetricsSnapshot(
            capability_alias=capability_alias,
            generated_at=utcnow(),
            plan_total=len(plans),
            terminal_total=terminal_total,
            completed_total=completed_total,
            failed_total=failed_total,
            rolled_back_total=rolled_back_total,
            success_rate=success_rate,
            rollback_rate=rollback_rate,
            avg_latency_ms=avg_latency_ms,
            p95_latency_ms=p95_latency_ms,
            total_cost_usd=total_cost_usd,
        )

    def evaluate_alerts(
        self,
        payload: HarnessAlertEvaluationRequest,
    ) -> HarnessAlertEvaluationResponse:
        metrics = self.get_metrics_snapshot(payload.capability_alias)
        thresholds = payload.thresholds
        alerts: list[HarnessAlert] = []

        if metrics.success_rate < thresholds.min_success_rate:
            alerts.append(
                HarnessAlert(
                    code="low_success_rate",
                    level="critical",
                    metric_value=metrics.success_rate,
                    threshold_value=thresholds.min_success_rate,
                    message="Success rate dropped below threshold",
                )
            )

        if (
            metrics.avg_latency_ms is not None
            and metrics.avg_latency_ms > thresholds.max_avg_latency_ms
        ):
            alerts.append(
                HarnessAlert(
                    code="high_avg_latency",
                    level="warning",
                    metric_value=metrics.avg_latency_ms,
                    threshold_value=thresholds.max_avg_latency_ms,
                    message="Average latency exceeds threshold",
                )
            )

        if metrics.total_cost_usd > thresholds.max_total_cost_usd:
            alerts.append(
                HarnessAlert(
                    code="high_total_cost",
                    level="warning",
                    metric_value=metrics.total_cost_usd,
                    threshold_value=thresholds.max_total_cost_usd,
                    message="Accumulated cost exceeds threshold",
                )
            )

        if metrics.rollback_rate > thresholds.max_rollback_rate:
            alerts.append(
                HarnessAlert(
                    code="high_rollback_rate",
                    level="critical",
                    metric_value=metrics.rollback_rate,
                    threshold_value=thresholds.max_rollback_rate,
                    message="Rollback rate exceeds threshold",
                )
            )

        return HarnessAlertEvaluationResponse(
            status="triggered" if alerts else "ok",
            metrics=metrics,
            alerts=alerts,
        )

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @staticmethod
    def _percentile(values: list[float], q: float) -> float:
        ordered = sorted(values)
        index = max(0, math.ceil(q * len(ordered)) - 1)
        return ordered[index]

    def _resolve_source_plan(
        self,
        trace_plan_ids: list[str],
        source_plan_id: str | None,
    ) -> PlanRecord:
        if source_plan_id:
            plan = self._plans.get(source_plan_id)
            if plan is None or source_plan_id not in trace_plan_ids:
                raise KeyError(source_plan_id)
            return plan

        return self._plans[trace_plan_ids[-1]]

    @staticmethod
    def _resolve_stable_checkpoint(
        events: list[RuntimeEventRecord],
    ) -> RuntimeEventRecord | None:
        stable_types = {
            RuntimeEventType.START,
            RuntimeEventType.PREPARE,
            RuntimeEventType.VALIDATE,
        }
        for event in reversed(events):
            if event.event_type in stable_types:
                return event
        return None

    @staticmethod
    def _checkpoint_event_chain(
        checkpoint: RuntimeEventRecord,
    ) -> list[RuntimeEventType]:
        if checkpoint.event_type is RuntimeEventType.START:
            return [
                RuntimeEventType.VALIDATE,
                RuntimeEventType.PREPARE,
                RuntimeEventType.START,
            ]
        if checkpoint.event_type is RuntimeEventType.PREPARE:
            return [
                RuntimeEventType.VALIDATE,
                RuntimeEventType.PREPARE,
            ]
        return [RuntimeEventType.VALIDATE]
