BEGIN;

DROP INDEX IF EXISTS idx_cp_usage_key_bucket;
DROP INDEX IF EXISTS idx_cp_usage_team_bucket;
DROP TABLE IF EXISTS cp_usage_fact;

DROP INDEX IF EXISTS idx_cp_audit_resource;
DROP INDEX IF EXISTS idx_cp_audit_team_time;
DROP TABLE IF EXISTS cp_audit_event;

COMMIT;
