# Change: Upgrade Admin Console to Platform Overview

## Why
The current 8000 admin page is useful for provider/key operations but still feels like a tool page, not a complete management platform. Operators need a single-page overview of governance and system status.

## What Changes
- Add `/api/platform/overview` to aggregate core governance metrics and internal service reachability.
- Add an overview tab on `/admin` with KPI cards, service status cards, and quick navigation to management modules.
- Keep 6333 (Qdrant) as internal infrastructure but visible in status cards for operators.

## Impact
- Affected specs: `admin-platform-overview`
- Affected code: `backend/app/routers/platform.py`, `backend/app/schemas.py`, `backend/app/main.py`, `backend/app/static/provider-console.html`, `backend/tests/test_app.py`
