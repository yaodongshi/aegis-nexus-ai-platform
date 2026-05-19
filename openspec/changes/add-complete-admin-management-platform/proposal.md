# Change: Build Complete Admin Management Platform

## Why
The current 3000 platform lacks durable account governance and complete operational UX. Users must re-register after reconstruction in some paths, and core capability pages (e.g., skill details) have been incomplete. A cohesive, admin-first platform is required.

## What Changes
- Introduce persistent user account storage with bootstrap admin support.
- Add admin user management (list/create/enable/disable) in platform settings.
- Standardize auth-expiry handling and forced re-login UX.
- Provide complete skill management UX (detail view, editability roadmap, lifecycle actions).
- Define a unified management console scope for users, providers, models, keys, skills, docs, and runtime health.
- Align implementation with proven patterns from mature open-source admin platforms (RBAC, auditability, safe defaults, idempotent bootstrap).

## Impact
- Affected code:
  - backend/app/api/v1/users.py
  - backend/app/user_schemas.py
  - frontend/src/lib/api.ts
  - frontend/src/pages/settings/index.tsx
  - frontend/src/pages/knowledge/index.tsx
- Affected areas:
  - Authentication and account lifecycle
  - Admin operation workflows
  - Skill management usability
- Breaking considerations:
  - None for existing API consumers in this phase; new endpoints are additive.
