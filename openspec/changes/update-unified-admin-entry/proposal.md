# Change: Unify Admin Entry

## Why

The current platform exposes multiple UI entrypoints with overlapping management concerns. Administrators currently discover and use the backend UI as `provider-console`, which understates its intended role as the unified control plane for providers, virtual keys, and future skill/knowledge governance.

## What Changes

- Add `/admin` as the primary backend management entrypoint while keeping `/provider-console` for compatibility.
- Rebrand the existing Provider Console as the Team AI Admin Console in UI text, tests, and public documentation.
- Update operator-facing docs to clarify that LiteLLM and Qdrant are internal data-plane services, while 8000 is the administrator entrypoint and 9000 is the team workspace.

## Impact

- Affected specs: `admin-entrypoint`
- Affected code: `backend/app/routers/provider_console.py`, `backend/app/static/provider-console.html`, `backend/tests/test_app.py`, `README.md`, `docs/user-guide.md`