# Change: Improve Key Ownership Management

## Why

The admin console can issue virtual keys, but it does not yet let administrators clearly manage which colleague or project owns each key. That makes team-level governance difficult even though the backend already stores `user_id` and `project_id`.

## What Changes

- Persist a human-readable `label` for each virtual key.
- Support admin-side filtering of keys by member, project, status, and keyword.
- Extend the admin UI so key issuance captures owner and project context explicitly.

## Impact

- Affected specs: `key-ownership-management`
- Affected code: `backend/app/schemas.py`, `backend/app/store.py`, `backend/app/routers/keys.py`, `backend/app/static/provider-console.html`, `backend/tests/test_app.py`, `docs/user-guide.md`