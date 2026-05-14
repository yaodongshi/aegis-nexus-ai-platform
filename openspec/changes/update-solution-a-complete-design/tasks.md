## 1. Architecture Finalization
- [ ] 1.1 Confirm Solution A layer boundaries and responsibility matrix.
- [ ] 1.2 Lock API boundary rules (`/api/v1/*` vs `/v1/*`).
- [ ] 1.3 Define security baseline for admin auth and virtual key handling.

## 2. Control Plane Implementation Plan
- [ ] 2.1 Complete virtual key and key policy API coverage (unit + API tests).
- [ ] 2.2 Align migrations with control-plane schema and rollback scripts.
- [ ] 2.3 Add governance endpoints for team/user ownership views.

## 3. Data Plane Integration Plan
- [ ] 3.1 Implement deterministic config generation for LiteLLM from control-plane state.
- [ ] 3.2 Add safe apply flow for LiteLLM config with validation checks.
- [ ] 3.3 Add E2E CLI matrix verification script and report output.

## 4. Observability Plan
- [ ] 4.1 Implement Langfuse integration profile as default.
- [ ] 4.2 Add optional Helicone profile for compatibility testing.
- [ ] 4.3 Build usage/audit reconciliation jobs and dashboard KPIs.

## 5. Skill/RAG Registry Plan
- [ ] 5.1 Define and create Skill registry schema and API endpoints.
- [ ] 5.2 Define and create RAG registry schema and API endpoints.
- [ ] 5.3 Implement cloud sync workflow with status tracking.

## 6. Validation and Delivery
- [ ] 6.1 Validate OpenSpec change with strict checks.
- [ ] 6.2 Update user-facing docs and operator runbook.
- [ ] 6.3 Execute MVP acceptance checklist and publish release notes.
