# Team AI Platform - Solution A Complete Design

Version: 1.0
Date: 2026-05-14
Status: Proposed (OpenSpec change: update-solution-a-complete-design)

## 1. Executive Summary
Solution A is the target architecture:
- Data Plane: LiteLLM (single OpenAI-compatible gateway)
- Observability Plane: Langfuse (default) or Helicone (optional profile)
- Control Plane: self-built FastAPI service for team governance, virtual key lifecycle, model authorization, and Skill/RAG registry

This architecture keeps all client integrations simple while centralizing governance and compliance.

## 2. Design Goals
- One endpoint strategy for heterogeneous CLI and SDK clients
- Strong governance for team, user, and virtual key ownership
- Policy-driven model authorization with auditability
- Cloud-ready Skill/RAG registration and synchronization
- Progressive rollout with low migration risk

## 3. High-Level Architecture

### 3.1 Control Plane
- Service: FastAPI (`backend/app`)
- API namespace: `/api/v1/*`
- Responsibilities:
  - Team/user ownership mapping
  - Virtual key lifecycle: create, list, revoke, rotate
  - Key policy: allow/deny models, quota, rpm, burst, emergency block
  - Skill/RAG registry metadata and sync status
  - Admin audit and reporting APIs
- Persistence: PostgreSQL

### 3.2 Data Plane
- Service: LiteLLM gateway
- API namespace: `/v1/*`
- Responsibilities:
  - Uniform protocol for all clients
  - Provider routing and fallback
  - Runtime policy constraints generated from control-plane state
- Inputs:
  - Generated configuration (models, keys, policy constraints)
- Outputs:
  - Completion responses
  - Trace metadata for observability

### 3.3 Observability Plane
- Default: Langfuse
- Alternative: Helicone (one active backend per env)
- Responsibilities:
  - Request traces and latency metrics
  - Prompt/response evaluation context
  - Usage and cost dashboards
  - Daily reconciliation with control-plane audit records

## 4. API Boundary Contract
- Control plane endpoints: `/api/v1/*`
  - Virtual key and policy management
  - Team/user governance
  - Skill/RAG registry and sync
- Data plane endpoints: `/v1/*`
  - Model listing and inference APIs (OpenAI-compatible)

Boundary rule: governance state changes never bypass control-plane APIs.

## 5. Governance Model

### 5.1 Ownership
- Virtual key fields:
  - `team_id`
  - `owner_type` (`user` | `project` | `service`)
  - `owner_id`

### 5.2 Lifecycle
- Active operations:
  - `create`
  - `revoke`
  - `rotate`
- Rotation invariant:
  - old key transitions to `revoked`
  - new key has `rotated_from = old_key_id`

### 5.3 Policy
- `allowed_models`
- `denied_models`
- `quota_tokens_day`
- `quota_tokens_month`
- `rate_limit_rpm`
- `burst_limit`
- `emergency_block`

## 6. Skill/RAG Cloud Design

### 6.1 Skill Registry
- Resource model:
  - identity, version, owner scope, status, manifest pointer
- Lifecycle:
  - draft -> validated -> published -> deprecated

### 6.2 RAG Registry
- Resource model:
  - dataset identity, embedding config, retention policy, sharing scope
- Lifecycle:
  - registered -> indexing -> active -> archived

### 6.3 Sync Workflow
- Trigger modes:
  - manual
  - event-driven (resource update)
- Status model:
  - `pending`
  - `running`
  - `succeeded`
  - `failed`
- Required metadata:
  - operator
  - timestamp
  - error summary (if failed)

## 7. Security Baseline
- Admin APIs protected by admin auth token or upstream auth gateway
- Virtual key secret is returned only on create/rotate, never persisted in plaintext
- Config sync pipeline is one-way from control plane to data plane
- Internal traffic should use private networking in production

## 8. Rollout Plan
1. Freeze architecture and OpenSpec contracts
2. Complete V2 key/policy test coverage and migration checks
3. Implement deterministic LiteLLM config generation and safe apply flow
4. Enable Langfuse integration and baseline dashboards
5. Add Skill/RAG registry APIs and sync workers
6. Execute CLI E2E matrix and release MVP

## 9. Acceptance Criteria
- Governance APIs and data-plane APIs are clearly separated and documented
- Key lifecycle and policy endpoints pass E2E tests
- LiteLLM config applies with health validation
- Langfuse telemetry is visible for all inference calls
- Skill/RAG resources support registry + sync status tracking

## 10. Open Questions
- Whether Helicone remains dev/test only or can be production fallback
- Whether time-window policy constraints are MVP scope or next phase
