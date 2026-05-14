BEGIN;

DROP INDEX IF EXISTS idx_cp_rag_sync_source_created;
DROP TABLE IF EXISTS cp_rag_sync_job;
DROP TABLE IF EXISTS cp_rag_source;

COMMIT;
