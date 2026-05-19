## 1. Implementation
- [x] 1.1 Persist user accounts in PostgreSQL and add bootstrap admin initialization.
- [x] 1.2 Add admin user management APIs (`list/create/status`).
- [x] 1.3 Add frontend settings user-management tab for admin users.
- [x] 1.4 Add global token-expiry handling and relogin recovery.
- [x] 1.5 Fix skill detail opening in knowledge/skills UI.

## 2. Validation
- [x] 2.1 Run focused backend auth tests in local `.venv`.
- [x] 2.2 Build and redeploy frontend/backend containers.
- [x] 2.3 Validate admin login + user list API + skill detail API/UI.

## 3. Follow-up (Next Iteration)
- [ ] 3.1 Add user edit (role/email), admin password reset, and transfer-admin flow. (user edit + admin reset password done; transfer-admin pending)
- [ ] 3.2 Add skill edit/version history and publish/unpublish lifecycle. (skill edit done; version history + publish lifecycle pending)
- [ ] 3.3 Add unified management dashboard cards with direct drill-down actions.
- [ ] 3.4 Add operator docs: bootstrap env vars, security hardening checklist.
