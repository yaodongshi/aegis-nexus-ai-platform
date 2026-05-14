## Context
The platform must support heterogeneous CLI clients while enforcing centralized governance. Team members should use existing tools without changing usage habits, and the platform should apply policy, observability, and Skill/RAG lifecycle centrally.

## Goals / Non-Goals
- Goals:
  - Provide one compatible inference endpoint for all CLI agents through LiteLLM.
  - Manage team/user/virtual-key/model-policy/Skill-RAG in one control plane.
  - Capture complete request traces and usage cost metrics with a pluggable observability layer.
  - Enable safe phased rollout from current V2 baseline.
- Non-Goals:
  - Replacing LiteLLM with a custom model gateway.
  - Supporting multiple observability systems at once in production by default.
  - Building tenant-specific custom protocol adapters in this phase.

## Decisions
- Decision: Use LiteLLM as the only runtime data-plane gateway.
  - Why: Maximum client compatibility and fastest integration path.
- Decision: Use Langfuse as default observability backend; keep Helicone as optional profile.
  - Why: Better trace and prompt analytics depth for team operations.
- Decision: Keep strict control/data path split.
  - Control plane: `backend/app` with admin APIs (`/api/v1/*`).
  - Data plane: LiteLLM runtime endpoint (`/v1/*`).
- Decision: Treat virtual keys as first-class governance resources with policy snapshots.
  - Why: Required for delegated ownership, revocation, rotation, and compliance auditing.
- Decision: Skill/RAG resources are registry entities under control plane governance.
  - Why: Needed for cloud synchronization and team-level reuse.

## Architecture
### Layer 1: Control Plane (FastAPI)
- Responsibilities:
  - Team and user identity mapping
  - Virtual key lifecycle (create/list/revoke/rotate)
  - Model authorization policy management
  - Skill and RAG registry metadata
  - Admin audit and usage query APIs
- Persistence:
  - PostgreSQL as source of truth

### Layer 2: Data Plane (LiteLLM)
- Responsibilities:
  - Normalize provider protocols into OpenAI-compatible API
  - Route requests based on allowed model set and fallback policy
  - Enforce per-key runtime constraints from control-plane generated config
- Inputs:
  - Generated/managed LiteLLM configuration from control-plane state
- Outputs:
  - Completion responses to CLI clients
  - Request metadata to observability layer

### Layer 3: Observability Plane (Langfuse preferred)
- Responsibilities:
  - Trace/span logging for inference calls
  - Prompt-response evaluation and cost breakdown
  - Team/project level dashboards and anomaly alerts
- Integration points:
  - LiteLLM callback hooks
  - Control-plane usage/audit reconciliation jobs

## Security and Trust Boundaries
- Admin APIs require admin token or equivalent auth gateway.
- Virtual key secret is write-only in create/rotate responses and never persisted in plaintext.
- Key policy updates are append/update controlled and auditable.
- Service-to-service traffic should run over private network paths in production.

## Data Model Summary
- `cp_virtual_key`
  - key ownership: team_id, owner_type, owner_id
  - lifecycle: status, rotated_from, revoked_at, expires_at
- `cp_key_policy`
  - allow/deny model lists
  - quotas and rate/burst limits
  - emergency block switch
- `cp_skill_registry` (planned)
  - skill identity, version, owner, status, manifest pointer
- `cp_rag_registry` (planned)
  - dataset identity, embedding settings, retention, sharing scope

## API Contract Summary
- Control plane (`/api/v1`)
  - `POST /keys`
  - `GET /keys`
  - `POST /keys/{key_id}/revoke`
  - `POST /keys/{key_id}/rotate`
  - `PUT /policies/keys/{key_id}`
  - `GET /policies/keys/{key_id}`
  - planned: Skill/RAG CRUD and sync endpoints
- Data plane (`/v1`)
  - OpenAI-compatible model and completion APIs served by LiteLLM

## Rollout Plan
1. Freeze architecture and contracts (this change).
2. Complete control-plane API tests and migration verification.
3. Add LiteLLM config sync pipeline from control-plane resources.
4. Enable Langfuse integration and baseline dashboards.
5. Add Skill/RAG registry APIs and sync workers.
6. Run E2E CLI verification matrix and cut MVP release.

## Risks / Trade-offs
- Risk: Config drift between control plane and LiteLLM runtime.
  - Mitigation: one-way generated config + health validation endpoint.
- Risk: Observability overhead and cost.
  - Mitigation: sampling controls and environment-based retention settings.
- Risk: Policy complexity can grow quickly.
  - Mitigation: policy templates and explicit precedence rules.

## Migration Plan
- Keep existing V2 API paths stable.
- Migrate legacy docs to `docs/user-guide-v2.md` and this design doc.
- Introduce new capabilities behind additive endpoints and migration scripts.

## Open Questions
- Whether Helicone profile should be kept only for dev/test or also production failover.
- Whether key policy should support time-window constraints in MVP or post-MVP.
