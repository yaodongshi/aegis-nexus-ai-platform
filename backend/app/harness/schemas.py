from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
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


class PlanCreateRequest(BaseModel):
    capability_alias: str = Field(..., min_length=1, max_length=128)
    strategy_id: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


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


def new_trace_id() -> str:
    return f"trace-{uuid4().hex}"


def utcnow() -> datetime:
    return datetime.now(UTC)
