# Change: Add Task-to-Skill Learning Loop with Sync

## Why
Team members complete tasks in external tools (Claude Code, Codex), but the platform still lacks an automatic path to capture outcomes, propose skill updates, apply them, and sync to reusable skill bundles.

## What Changes
- Add task reporting endpoint for tool-side completion callbacks.
- Auto-create skill update proposals from task reports.
- Add apply and sync operations for skill updates (local export and Git sync).
- Add database schema support for task runs and skill updates.

## Impact
- Affected specs: `learning-loop-skill-sync`
- Affected code: `backend/app/routers/learning.py`, `backend/app/store.py`, `backend/app/schemas.py`, `backend/app/main.py`, `backend/tests/test_app.py`
