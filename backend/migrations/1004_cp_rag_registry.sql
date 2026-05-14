BEGIN;

CREATE TABLE IF NOT EXISTS cp_rag_source (
  source_id TEXT PRIMARY KEY,
  team_id TEXT,
  project_id TEXT,
  name TEXT NOT NULL,
  connector_type TEXT NOT NULL,
  scope TEXT NOT NULL,
  config_json JSONB NOT NULL,
  access_policy JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'active',
  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cp_rag_sync_job (
  job_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES cp_rag_source(source_id),
  trigger_type TEXT NOT NULL,
  status TEXT NOT NULL,
  snapshot_ref TEXT,
  stats_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cp_rag_sync_source_created
  ON cp_rag_sync_job(source_id, created_at DESC);

COMMIT;
