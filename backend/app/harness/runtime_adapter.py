from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .role_executor import EvaluatorExecutor, PlannerExecutor, WorkerExecutor
from .schemas import PlanRecord


class RuntimeAdapter(Protocol):
    name: str

    def validate_plan(self, plan: PlanRecord) -> None:
        ...

    def start_plan(self, plan: PlanRecord) -> dict[str, Any]:
        ...


@dataclass
class NoopRuntimeAdapter:
    name: str = "noop"

    def validate_plan(self, plan: PlanRecord) -> None:
        if not plan.capability_alias.strip():
            raise ValueError("capability_alias is required")

    def start_plan(self, plan: PlanRecord) -> dict[str, Any]:
        # Skeleton runtime path: real engine integration (LangGraph/Agents SDK)
        # should be implemented in dedicated adapters.
        return {
            "status": "started",
            "adapter": self.name,
            "plan_id": plan.plan_id,
        }


@dataclass
class LocalGraphRuntimeAdapter:
    name: str = "local-graph"

    def __post_init__(self) -> None:
        self._planner = PlannerExecutor()
        self._worker = WorkerExecutor()
        self._evaluator = EvaluatorExecutor()

    def validate_plan(self, plan: PlanRecord) -> None:
        if not plan.capability_alias.strip():
            raise ValueError("capability_alias is required")

    def start_plan(self, plan: PlanRecord) -> dict[str, Any]:
        context = self._planner.build_execution_context(plan)
        worker_result = self._worker.run(context)
        evaluation = self._evaluator.evaluate(worker_result)
        return {
            "status": "started",
            "adapter": self.name,
            "context": context,
            "worker_result": worker_result,
            "evaluation": evaluation,
            "latency_ms": worker_result.get("latency_ms", 100.0),
            "cost_usd": worker_result.get("cost_usd", 0.01),
        }


class RuntimeAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, RuntimeAdapter] = {
            "noop": NoopRuntimeAdapter(),
            "local-graph": LocalGraphRuntimeAdapter(),
        }

    def register(self, adapter: RuntimeAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def resolve(self, name: str | None) -> RuntimeAdapter:
        key = name or "noop"
        adapter = self._adapters.get(key)
        if adapter is None:
            raise KeyError(f"unknown runtime adapter: {key}")
        return adapter
