# V2 Control Plane Migrations

## Scope

This directory stores PostgreSQL schema migrations for the V2 control plane.

## Apply Order

1. 1001_cp_identity.sql
2. 1002_cp_virtual_key_and_policy.sql
3. 1003_cp_skill_registry.sql
4. 1004_cp_rag_registry.sql
5. 1005_cp_audit_and_usage.sql

## Rollback Order

1. rollback/1005_cp_audit_and_usage.rollback.sql
2. rollback/1004_cp_rag_registry.rollback.sql
3. rollback/1003_cp_skill_registry.rollback.sql
4. rollback/1002_cp_virtual_key_and_policy.rollback.sql
5. rollback/1001_cp_identity.rollback.sql

## Manual Apply Example

```bash
psql "$TEAM_AI_PLATFORM_DB_DSN" -f backend/migrations/1001_cp_identity.sql
psql "$TEAM_AI_PLATFORM_DB_DSN" -f backend/migrations/1002_cp_virtual_key_and_policy.sql
psql "$TEAM_AI_PLATFORM_DB_DSN" -f backend/migrations/1003_cp_skill_registry.sql
psql "$TEAM_AI_PLATFORM_DB_DSN" -f backend/migrations/1004_cp_rag_registry.sql
psql "$TEAM_AI_PLATFORM_DB_DSN" -f backend/migrations/1005_cp_audit_and_usage.sql
```

## Manual Rollback Example

```bash
psql "$TEAM_AI_PLATFORM_DB_DSN" -f backend/migrations/rollback/1005_cp_audit_and_usage.rollback.sql
psql "$TEAM_AI_PLATFORM_DB_DSN" -f backend/migrations/rollback/1004_cp_rag_registry.rollback.sql
psql "$TEAM_AI_PLATFORM_DB_DSN" -f backend/migrations/rollback/1003_cp_skill_registry.rollback.sql
psql "$TEAM_AI_PLATFORM_DB_DSN" -f backend/migrations/rollback/1002_cp_virtual_key_and_policy.rollback.sql
psql "$TEAM_AI_PLATFORM_DB_DSN" -f backend/migrations/rollback/1001_cp_identity.rollback.sql
```

## Notes

- Keep migrations append-only.
- Avoid editing applied SQL files.
- Any schema change must include a rollback script.
