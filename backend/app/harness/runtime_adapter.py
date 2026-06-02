from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .schemas import PlanRecord


class RuntimeAdapter(Protocol):
    name: str

    def validate_plan(self, plan: PlanRecord) -> None:
        ...

    def start_plan(self, plan: PlanRecord) -> None:
        ...


@dataclass
class NoopRuntimeAdapter:
    name: str = "noop"

    def validate_plan(self, plan: PlanRecord) -> None:
        if not plan.capability_alias.strip():
            raise ValueError("capability_alias is required")

    def start_plan(self, plan: PlanRecord) -> None:
        # Skeleton runtime path: real engine integration (LangGraph/Agents SDK)
        # should be implemented in dedicated adapters.
        return


class RuntimeAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, RuntimeAdapter] = {
            "noop": NoopRuntimeAdapter()
        }

    def register(self, adapter: RuntimeAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def resolve(self, name: str | None) -> RuntimeAdapter:
        key = name or "noop"
        adapter = self._adapters.get(key)
        if adapter is None:
            raise KeyError(f"unknown runtime adapter: {key}")
        return adapter
