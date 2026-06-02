## 1. Planning and Contracts

- [x] 1.1 Define `harness-runtime` capability spec and validate OpenSpec format.
- [x] 1.2 Define task plan state machine and invalid transition rules.
- [x] 1.3 Define runtime event schema (`RuntimeEvent`) and trace propagation fields.
- [x] 1.4 Define capability alias contract versioning and rollout metadata.

## 2. Runtime Foundation

- [x] 2.1 Create `backend/app/harness/` module skeleton (`runtime_adapter.py`, `plan_lock.py`, `role_executor.py`, `trace_bridge.py`).
- [x] 2.2 Implement Task Plan Lock persistence and transition guard.
- [x] 2.3 Add runtime adapter interface and one concrete adapter path.
- [x] 2.4 Add harness router (`/api/v1/harness/*`) for plan creation, state query, and event ingestion.

## 3. Governance and Rollout

- [x] 3.1 Implement strategy rollout service (`canary`, `promote`, `demote`, `rollback`).
- [x] 3.2 Bind rollout policy to capability aliases in control-plane.
- [x] 3.3 Add approval gate hooks for risky transitions.
- [x] 3.4 Add immutable audit records for rollout decisions.

## 4. Observability and Safety

- [x] 4.1 Standardize `trace_id` generation and propagation across frontend/backend/gateway.
- [x] 4.2 Add dashboard metrics for success rate, latency, cost, rollback rate.
- [x] 4.3 Add alerting rules for regression thresholds.
- [x] 4.4 Add replay tooling for failed plan investigation.

## 5. Open-Source Integration Path

- [x] 5.1 Integrate first runtime backend (LangGraph or OpenAI Agents SDK) via adapter.
- [x] 5.2 Implement conformance test suite to verify adapter behavior.
- [x] 5.3 Document license/compliance checklist for reused open-source components.
- [x] 5.4 Run pilot on one production-like capability alias and collect baseline metrics.

## 6. Delivery and Acceptance

- [x] 6.1 Publish updated docs and migration runbook.
- [x] 6.2 Complete end-to-end validation: create plan -> run -> promote/rollback -> audit/replay.
- [x] 6.3 Execute rollback drill and capture evidence.
- [x] 6.4 Final acceptance review with architecture and product stakeholders.
