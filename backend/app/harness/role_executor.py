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
        return {"status": "started", "context": context}


@dataclass
class EvaluatorExecutor:
    def evaluate(self, result: dict[str, Any]) -> dict[str, Any]:
        # Placeholder for rollout metrics hookup.
        return {"accepted": True, "result": result}
