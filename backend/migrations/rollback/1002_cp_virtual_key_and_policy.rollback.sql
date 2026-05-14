BEGIN;

DROP INDEX IF EXISTS idx_cp_key_policy_key;
DROP TABLE IF EXISTS cp_key_policy;

DROP INDEX IF EXISTS idx_cp_virtual_key_owner;
DROP INDEX IF EXISTS idx_cp_virtual_key_team_status;
DROP TABLE IF EXISTS cp_virtual_key;

COMMIT;
