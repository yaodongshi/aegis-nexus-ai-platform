## Context
The platform has evolved quickly around LiteLLM/provider/skill/rag operations, but management workflows remained fragmented. Account data was previously memory-backed, and feature usability gaps existed in the skill UI.

## Goals / Non-Goals
- Goals:
  - Durable user identity and admin bootstrap without manual recreation on service rebuild.
  - Admin-operable account controls from web UI.
  - Deterministic auth-expiry behavior across all API paths.
  - Skill detail access and operator-grade management UX baseline.
- Non-Goals:
  - Full enterprise IAM federation (SSO/OIDC/SAML) in this change.
  - Multi-organization billing and advanced tenancy isolation redesign.

## Decisions
- Decision: Persist auth users into PostgreSQL table `backend_auth_users` with indexed role/status.
  - Why: survive restart/rebuild and keep operational behavior deterministic.
- Decision: Auto-bootstrap one admin account via environment-driven defaults.
  - Why: guarantee first-login operability on fresh deployment.
- Decision: Keep self-registration role fixed to `member`; admin role managed only by admin endpoints.
  - Why: reduce privilege escalation risk.
- Decision: Add admin user operations under `/api/v1/users/admin/*`.
  - Why: explicit governance API boundary.
- Decision: Fix skill detail UX inside existing Knowledge page before introducing dedicated detail route.
  - Why: fast recovery of missing core workflow with minimal disruption.

## Risks / Trade-offs
- Risk: default bootstrap admin password could be weak in unmanaged environments.
  - Mitigation: document and enforce environment override in deployment checklist.
- Risk: additive admin APIs may need future RBAC granularity.
  - Mitigation: keep endpoint namespace and payloads extensible.

## Migration Plan
1. Deploy backend with user table auto-creation and bootstrap admin logic.
2. Deploy frontend with settings user-management tab and skill detail panel.
3. Verify admin login, user CRUD-lite operations, and skill detail opening.
4. Follow-up phase: add user edit/reset-password/admin transfer and audit logs.

## Open Questions
- Should self-registration be disabled by default in production profile?
- Should admin bootstrap be one-time token-gated rather than password-based default?
