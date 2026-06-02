## Context

Team AI Platform already behaves like a governance-centric control plane with an evolving knowledge loop, but runtime determinism is weak. We need an advanced yet extensible architecture that keeps governance central and allows runtime innovation without contract breakage.

## Goals / Non-Goals

Goals:
- Introduce a pluggable harness runtime layer.
- Enforce deterministic execution via state machine lock.
- Support strategy canary rollout and automatic rollback.
- Preserve stable capability contracts for business integration.
- Enable runtime engine swap with minimal business impact.

Non-Goals:
- Replacing LiteLLM gateway responsibilities.
- Rewriting existing control-plane governance APIs from scratch.
- Full multi-tenant billing refactor in this change.

## Architecture Decisions

Decision 1: Dual-layer design
- Keep control-plane as source of truth.
- Route all runtime events through a harness adapter.

Decision 2: Tool-driven state progression
- Only validated tool/runtime events can transition task state.
- LLM output alone cannot set terminal state.

Decision 3: Capability virtualization
- Expose business-facing capability aliases (`chat-default`, `embed-default`, future `reasoning-default`).
- Bind rollout, policy, and guardrails at capability layer.

Decision 4: Progressive automation
- Start with manual approval gates.
- Add metric-based auto-promotion after confidence thresholds.

## Open-Source Adoption Strategy

Primary engines:
- LangGraph for durable graph execution and HITL interruptions.
- OpenAI Agents SDK for guardrails/sessions/tracing/sandbox patterns.

Reference-only:
- OpenHands for software-agent workflows.
- CrewAI for flow composition ergonomics.

Adoption method:
- Build adapters and contracts first.
- Port minimal execution paths with integration tests.
- Avoid direct business logic copy; preserve clear module boundaries.

## Data and Event Model

TaskPlan:
- `plan_id`, `capability`, `version`, `owner`, `state`, `strategy_id`, `trace_id`.

TaskState:
- `created`, `validated`, `ready`, `running`, `blocked`, `failed`, `completed`, `rolled_back`.

RuntimeEvent:
- `event_id`, `plan_id`, `event_type`, `source`, `payload`, `occurred_at`, `trace_id`.

PromotionRecord:
- `strategy_id`, `window`, `baseline_metrics`, `candidate_metrics`, `decision`, `decided_at`.

## Risks / Trade-offs

- Risk: adapter complexity across multiple runtimes.
  - Mitigation: single internal event contract and conformance tests.
- Risk: delayed delivery due to over-engineering.
  - Mitigation: strict phase gates and MVP-first scope.
- Risk: unsafe auto-promotion.
  - Mitigation: bounded canary, hard stop thresholds, one-click rollback.

## Migration Plan

1. Introduce harness runtime interfaces without changing external APIs.
2. Add Task Plan Lock and event schema.
3. Migrate one critical flow to runtime adapter path.
4. Enable canary strategy rollout on one capability alias.
5. Expand to broader capabilities after stability baseline.

## Validation Plan

- Contract tests for runtime event schema.
- State machine transition tests with invalid transition rejection.
- Rollback simulation tests under forced failure conditions.
- Observability tests to verify trace propagation across layers.

## Open Questions

- Which first runtime path should be migrated (learning replay vs approval-bound workflows)?
- Which metric thresholds are used for auto-promote in phase 1 (cost vs latency priority)?
- Should strategy decisions require explicit approver for P0/P1 capabilities?
