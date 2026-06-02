from __future__ import annotations

import pytest

from backend.app.harness.runtime_adapter import (
    LocalGraphRuntimeAdapter,
    NoopRuntimeAdapter,
    RuntimeAdapterRegistry,
)
from backend.app.harness.schemas import PlanRecord, PlanState, utcnow


def _plan(capability_alias: str = "chat-default") -> PlanRecord:
    now = utcnow()
    return PlanRecord(
        plan_id="plan-test",
        trace_id="trace-test",
        capability_alias=capability_alias,
        strategy_id="strategy-test",
        state=PlanState.CREATED,
        metadata={"runtime_adapter": "noop"},
        created_at=now,
        updated_at=now,
    )


@pytest.mark.parametrize(
    "adapter_cls, expected_name",
    [
        (NoopRuntimeAdapter, "noop"),
        (LocalGraphRuntimeAdapter, "local-graph"),
    ],
)
def test_adapter_conformance_validate_and_start(
    adapter_cls,
    expected_name: str,
) -> None:
    adapter = adapter_cls()
    plan = _plan("chat-default")

    adapter.validate_plan(plan)
    output = adapter.start_plan(plan)

    assert isinstance(output, dict)
    assert output["status"] == "started"
    assert output["adapter"] == expected_name


@pytest.mark.parametrize(
    "adapter_cls",
    [NoopRuntimeAdapter, LocalGraphRuntimeAdapter],
)
def test_adapter_conformance_rejects_empty_capability(adapter_cls) -> None:
    adapter = adapter_cls()
    plan = _plan("   ")

    with pytest.raises(ValueError):
        adapter.validate_plan(plan)


def test_runtime_adapter_registry_resolves_expected_adapters() -> None:
    registry = RuntimeAdapterRegistry()

    noop = registry.resolve("noop")
    local_graph = registry.resolve("local-graph")

    assert noop.name == "noop"
    assert local_graph.name == "local-graph"
