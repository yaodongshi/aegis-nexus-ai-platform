BEGIN;

CREATE TABLE IF NOT EXISTS cp_audit_event (
  event_id TEXT PRIMARY KEY,
  team_id TEXT,
  actor_id TEXT,
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  before_json JSONB,
  after_json JSONB,
  reason TEXT,
  request_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  integrity_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cp_audit_team_time
  ON cp_audit_event(team_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_cp_audit_resource
  ON cp_audit_event(resource_type, resource_id, created_at DESC);

CREATE TABLE IF NOT EXISTS cp_usage_fact (
  fact_id BIGSERIAL PRIMARY KEY,
  team_id TEXT,
  user_id TEXT,
  key_id TEXT,
  model TEXT,
  provider TEXT,
  skill_id TEXT,
  rag_source_id TEXT,
  request_count INTEGER NOT NULL DEFAULT 0,
  input_tokens BIGINT NOT NULL DEFAULT 0,
  output_tokens BIGINT NOT NULL DEFAULT 0,
  total_cost_usd NUMERIC(20, 8) NOT NULL DEFAULT 0,
  error_count INTEGER NOT NULL DEFAULT 0,
  ts_bucket TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cp_usage_team_bucket
  ON cp_usage_fact(team_id, ts_bucket DESC);

CREATE INDEX IF NOT EXISTS idx_cp_usage_key_bucket
  ON cp_usage_fact(key_id, ts_bucket DESC);

COMMIT;
