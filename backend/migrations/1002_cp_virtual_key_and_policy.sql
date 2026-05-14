BEGIN;

CREATE TABLE IF NOT EXISTS cp_virtual_key (
  key_id TEXT PRIMARY KEY,
  team_id TEXT NOT NULL REFERENCES cp_team(team_id),
  alias TEXT,
  key_hash TEXT NOT NULL UNIQUE,
  owner_type TEXT NOT NULL,
  owner_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  expires_at TIMESTAMPTZ,
  rotated_from TEXT,
  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cp_virtual_key_team_status
  ON cp_virtual_key(team_id, status);

CREATE INDEX IF NOT EXISTS idx_cp_virtual_key_owner
  ON cp_virtual_key(owner_type, owner_id);

CREATE TABLE IF NOT EXISTS cp_key_policy (
  policy_id TEXT PRIMARY KEY,
  key_id TEXT NOT NULL REFERENCES cp_virtual_key(key_id),
  allowed_models JSONB NOT NULL DEFAULT '[]'::jsonb,
  denied_models JSONB NOT NULL DEFAULT '[]'::jsonb,
  quota_tokens_day BIGINT,
  quota_tokens_month BIGINT,
  rate_limit_rpm INTEGER,
  burst_limit INTEGER,
  emergency_block BOOLEAN NOT NULL DEFAULT FALSE,
  effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  effective_to TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cp_key_policy_key
  ON cp_key_policy(key_id);

COMMIT;
