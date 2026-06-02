from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class PlanState(StrEnum):
    CREATED = "created"
    VALIDATED = "validated"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    FAILED = "failed"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


class RuntimeEventType(StrEnum):
    VALIDATE = "validate"
    PREPARE = "prepare"
    START = "start"
    BLOCK = "block"
    FAIL = "fail"
    COMPLETE = "complete"
    ROLLBACK = "rollback"


class RolloutAction(StrEnum):
    CANARY = "canary"
    PROMOTE = "promote"
    DEMOTE = "demote"
    ROLLBACK = "rollback"


class PlanCreateRequest(BaseModel):
    capability_alias: str = Field(..., min_length=1, max_length=128)
    strategy_id: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityAliasContractUpsertRequest(BaseModel):
    contract_version: str = Field(default="v1", min_length=1, max_length=32)
    runtime_adapter: str = Field(default="noop", min_length=1, max_length=64)
    stable_strategy_id: str | None = Field(default=None, max_length=128)
    canary_strategy_id: str | None = Field(default=None, max_length=128)
    canary_traffic_percent: int = Field(default=0, ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityAliasContractRecord(BaseModel):
    capability_alias: str
    contract_version: str
    runtime_adapter: str
    stable_strategy_id: str | None = None
    canary_strategy_id: str | None = None
    canary_traffic_percent: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class RolloutDecisionRequest(BaseModel):
    action: RolloutAction
    candidate_strategy_id: str | None = Field(default=None, max_length=128)
    canary_traffic_percent: int | None = Field(default=None, ge=0, le=100)
    approval_id: str | None = Field(default=None, max_length=128)
    baseline_metrics: dict[str, float] = Field(default_factory=dict)
    candidate_metrics: dict[str, float] = Field(default_factory=dict)
    thresholds: dict[str, float] = Field(default_factory=dict)
    actor: str = Field(default="system", min_length=1, max_length=128)
    rationale: str | None = Field(default=None, max_length=2048)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RolloutDecisionRecord(BaseModel):
    decision_id: str
    capability_alias: str
    action: RolloutAction
    approval_id: str | None = None
    approval_status: str | None = None
    stable_strategy_before: str | None = None
    canary_strategy_before: str | None = None
    stable_strategy_after: str | None = None
    canary_strategy_after: str | None = None
    canary_traffic_percent_after: int
    baseline_metrics: dict[str, float] = Field(default_factory=dict)
    candidate_metrics: dict[str, float] = Field(default_factory=dict)
    thresholds: dict[str, float] = Field(default_factory=dict)
    actor: str
    rationale: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    decided_at: datetime


class PlanRecord(BaseModel):
    plan_id: str
    trace_id: str
    capability_alias: str
    strategy_id: str | None = None
    state: PlanState
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class RuntimeEventIngestRequest(BaseModel):
    event_type: RuntimeEventType
    source: str = Field(..., min_length=1, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)


class RuntimeEventRecord(BaseModel):
    event_id: str
    plan_id: str
    trace_id: str
    event_type: RuntimeEventType
    source: str
    payload: dict[str, Any]
    occurred_at: datetime


class RuntimeEventIngestResponse(BaseModel):
    plan: PlanRecord
    event: RuntimeEventRecord


class TraceEventsResponse(BaseModel):
    trace_id: str
    plans: list[PlanRecord]
    events: list[RuntimeEventRecord]


class HarnessMetricsSnapshot(BaseModel):
    capability_alias: str | None = None
    generated_at: datetime
    plan_total: int = 0
    terminal_total: int = 0
    completed_total: int = 0
    failed_total: int = 0
    rolled_back_total: int = 0
    success_rate: float = 0.0
    rollback_rate: float = 0.0
    avg_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    total_cost_usd: float = 0.0


class HarnessAlertThresholds(BaseModel):
    min_success_rate: float = Field(default=0.95, ge=0.0, le=1.0)
    max_avg_latency_ms: float = Field(default=1500.0, ge=0.0)
    max_total_cost_usd: float = Field(default=200.0, ge=0.0)
    max_rollback_rate: float = Field(default=0.05, ge=0.0, le=1.0)


class HarnessAlert(BaseModel):
    code: str
    level: Literal["warning", "critical"]
    metric_value: float
    threshold_value: float
    message: str


class HarnessAlertEvaluationRequest(BaseModel):
    capability_alias: str | None = Field(default=None, max_length=128)
    thresholds: HarnessAlertThresholds = Field(
        default_factory=HarnessAlertThresholds,
    )


class HarnessAlertEvaluationResponse(BaseModel):
    status: Literal["ok", "triggered"]
    metrics: HarnessMetricsSnapshot
    alerts: list[HarnessAlert] = Field(default_factory=list)


def new_trace_id() -> str:
    return f"trace-{uuid4().hex}"


def utcnow() -> datetime:
    return datetime.now(UTC)
