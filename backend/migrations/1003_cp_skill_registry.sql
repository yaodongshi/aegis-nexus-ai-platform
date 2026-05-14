BEGIN;

CREATE TABLE IF NOT EXISTS cp_skill (
  skill_id TEXT PRIMARY KEY,
  team_id TEXT,
  project_id TEXT,
  name TEXT NOT NULL,
  current_version TEXT,
  owner_scope TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(team_id, name)
);

CREATE TABLE IF NOT EXISTS cp_skill_release (
  release_id TEXT PRIMARY KEY,
  skill_id TEXT NOT NULL REFERENCES cp_skill(skill_id),
  version TEXT NOT NULL,
  channel TEXT NOT NULL,
  manifest_json JSONB NOT NULL,
  policy_json JSONB NOT NULL,
  signature TEXT,
  rollout_percent INTEGER NOT NULL DEFAULT 100,
  status TEXT NOT NULL DEFAULT 'published',
  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(skill_id, version, channel)
);

CREATE INDEX IF NOT EXISTS idx_cp_skill_release_skill_channel
  ON cp_skill_release(skill_id, channel, created_at DESC);

COMMIT;
