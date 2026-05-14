BEGIN;

DROP INDEX IF EXISTS idx_cp_skill_release_skill_channel;
DROP TABLE IF EXISTS cp_skill_release;
DROP TABLE IF EXISTS cp_skill;

COMMIT;
