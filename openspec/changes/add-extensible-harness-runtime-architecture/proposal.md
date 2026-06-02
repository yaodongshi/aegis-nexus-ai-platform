# Change: Add Extensible Harness Runtime Architecture

## Why

Current platform has a strong control-plane foundation (policies, approvals, key governance, gateway sync, audit), but lacks a hard-constrained execution runtime. This creates risk in task determinism, rollback safety, and scalable self-evolution.

The team requested a full next-step plan with open-source harness research and executable tasks, aligned with OpenSpec.

## What Changes

- Add a new capability spec: `harness-runtime`.
- Define a dual-layer architecture:
  - Control Plane remains source of truth.
  - Harness Runtime becomes pluggable execution kernel.
- Standardize execution state machine (Task Plan Lock) with tool-only state transitions.
- Add strategy rollout controls (canary, rollback, promote/demote).
- Add unified tracing contract across frontend, backend, and gateway.
- Add open-source adoption path (LangGraph / OpenAI Agents SDK first; OpenHands/CrewAI as selective references).

## Current Architecture Analysis (As-Is)

Strengths:
- Control-plane APIs and governance primitives already exist.
- LiteLLM runtime config sync and audit rollback path are in place.
- Learning/evolution APIs already provide workflow generation and replay primitives.

Gaps:
- No strict runtime lock/state machine to prevent model self-claim completion.
- No explicit planner/executor/evaluator runtime separation.
- No automated strategy compare-and-promote lifecycle.
- Tracing is not normalized end-to-end.

## Open-Source Research Summary

- LangGraph: best for durable stateful execution and HITL.
- OpenAI Agents SDK: best for guardrails, sessions, tracing, and sandbox-style execution.
- OpenHands: strong software-agent execution reference, but enterprise boundaries and licensing differences must be respected.
- CrewAI: useful flow composition patterns; control-plane remains external.

## Copying Policy from GitHub

- Allowed: architectural patterns, interfaces, test design, adaptation wrappers.
- Not recommended: wholesale business logic copying.
- Required: license compliance, attribution, and internal abstraction boundaries.

## Impact

- Affected specs: `harness-runtime`, `control-plane`, `gitops-evolution-loop`.
- Affected code (planned):
  - `backend/app/harness/*`
  - `backend/app/routers/harness.py`
  - `backend/app/services/strategy_rollout.py`
  - `backend/app/schemas/plan_state.py`
- Affected docs:
  - `docs/MASTER_ARCHITECTURE_ANALYSIS_AND_TARGET_2026-06-02.md`
  - `docs/MASTER_EXECUTION_PLAN_2026-06-02.md`
  - `docs/HARNESS_OPEN_SOURCE_IMPLEMENTATION_BLUEPRINT_2026-06-02.md`
