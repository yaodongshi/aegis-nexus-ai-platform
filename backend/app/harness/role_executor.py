from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schemas import PlanRecord


@dataclass
class PlannerExecutor:
    def build_execution_context(self, plan: PlanRecord) -> dict[str, Any]:
        return {
            "plan_id": plan.plan_id,
            "capability_alias": plan.capability_alias,
            "strategy_id": plan.strategy_id,
            "state": plan.state,
        }


@dataclass
class WorkerExecutor:
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        # Placeholder for engine-specific execution payloads.
        capability_alias = str(context.get("capability_alias", ""))
        latency_ms = 80.0 + float(len(capability_alias))
        cost_usd = 0.01 + float(len(capability_alias)) / 10000.0
        return {
            "status": "started",
            "context": context,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
        }


@dataclass
class EvaluatorExecutor:
    def evaluate(self, result: dict[str, Any]) -> dict[str, Any]:
        # Placeholder for rollout metrics hookup.
        return {"accepted": True, "result": result}
