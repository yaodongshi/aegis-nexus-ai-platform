# Aegis Nexus V2 数据模型与迁移计划

> 文档定位：控制面数据库施工蓝图（PostgreSQL）。

## 1. 目标

- 支持团队/用户/虚拟 key/策略/Skill/RAG/审计的统一治理
- 兼容当前后端已有模型、key、skill、policy 基础能力
- 支持分阶段迁移，不中断现有网关调用

## 2. 逻辑实体

- Team
- User
- Membership
- VirtualKey
- KeyPolicy
- Skill
- SkillRelease
- RagSource
- RagSyncJob
- AuditEvent
- UsageFact

## 3. 物理表设计（PostgreSQL）

## 3.1 组织与身份

```sql
CREATE TABLE cp_team (
  team_id          TEXT PRIMARY KEY,
  name             TEXT NOT NULL,
  slug             TEXT NOT NULL UNIQUE,
  status           TEXT NOT NULL DEFAULT 'active',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cp_user (
  user_id          TEXT PRIMARY KEY,
  email            TEXT,
  display_name     TEXT,
  identity_provider TEXT,
  identity_sub     TEXT,
  status           TEXT NOT NULL DEFAULT 'active',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cp_membership (
  team_id          TEXT NOT NULL REFERENCES cp_team(team_id),
  user_id          TEXT NOT NULL REFERENCES cp_user(user_id),
  role             TEXT NOT NULL,
  status           TEXT NOT NULL DEFAULT 'active',
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (team_id, user_id)
);
```

## 3.2 虚拟 Key 与策略

```sql
CREATE TABLE cp_virtual_key (
  key_id           TEXT PRIMARY KEY,
  team_id          TEXT NOT NULL REFERENCES cp_team(team_id),
  alias            TEXT,
  key_hash         TEXT NOT NULL UNIQUE,
  owner_type       TEXT NOT NULL,
  owner_id         TEXT NOT NULL,
  status           TEXT NOT NULL DEFAULT 'active',
  expires_at       TIMESTAMPTZ,
  rotated_from     TEXT,
  created_by       TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at       TIMESTAMPTZ
);

CREATE INDEX idx_cp_virtual_key_team_status ON cp_virtual_key(team_id, status);
CREATE INDEX idx_cp_virtual_key_owner ON cp_virtual_key(owner_type, owner_id);

CREATE TABLE cp_key_policy (
  policy_id        TEXT PRIMARY KEY,
  key_id           TEXT NOT NULL REFERENCES cp_virtual_key(key_id),
  allowed_models   JSONB NOT NULL DEFAULT '[]'::jsonb,
  denied_models    JSONB NOT NULL DEFAULT '[]'::jsonb,
  quota_tokens_day BIGINT,
  quota_tokens_month BIGINT,
  rate_limit_rpm   INTEGER,
  burst_limit      INTEGER,
  emergency_block  BOOLEAN NOT NULL DEFAULT FALSE,
  effective_from   TIMESTAMPTZ NOT NULL DEFAULT now(),
  effective_to     TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cp_key_policy_key ON cp_key_policy(key_id);
```

## 3.3 Skill 与发布

```sql
CREATE TABLE cp_skill (
  skill_id         TEXT PRIMARY KEY,
  team_id          TEXT,
  project_id       TEXT,
  name             TEXT NOT NULL,
  current_version  TEXT,
  owner_scope      TEXT NOT NULL,
  status           TEXT NOT NULL DEFAULT 'active',
  created_by       TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(team_id, name)
);

CREATE TABLE cp_skill_release (
  release_id       TEXT PRIMARY KEY,
  skill_id         TEXT NOT NULL REFERENCES cp_skill(skill_id),
  version          TEXT NOT NULL,
  channel          TEXT NOT NULL,
  manifest_json    JSONB NOT NULL,
  policy_json      JSONB NOT NULL,
  signature        TEXT,
  rollout_percent  INTEGER NOT NULL DEFAULT 100,
  status           TEXT NOT NULL DEFAULT 'published',
  created_by       TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(skill_id, version, channel)
);

CREATE INDEX idx_cp_skill_release_skill_channel ON cp_skill_release(skill_id, channel, created_at DESC);
```

## 3.4 RAG 数据源与同步

```sql
CREATE TABLE cp_rag_source (
  source_id        TEXT PRIMARY KEY,
  team_id          TEXT,
  project_id       TEXT,
  name             TEXT NOT NULL,
  connector_type   TEXT NOT NULL,
  scope            TEXT NOT NULL,
  config_json      JSONB NOT NULL,
  access_policy    JSONB NOT NULL DEFAULT '{}'::jsonb,
  status           TEXT NOT NULL DEFAULT 'active',
  created_by       TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cp_rag_sync_job (
  job_id           TEXT PRIMARY KEY,
  source_id        TEXT NOT NULL REFERENCES cp_rag_source(source_id),
  trigger_type     TEXT NOT NULL,
  status           TEXT NOT NULL,
  snapshot_ref     TEXT,
  stats_json       JSONB NOT NULL DEFAULT '{}'::jsonb,
  started_at       TIMESTAMPTZ,
  finished_at      TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cp_rag_sync_source_created ON cp_rag_sync_job(source_id, created_at DESC);
```

## 3.5 审计与用量事实表

```sql
CREATE TABLE cp_audit_event (
  event_id         TEXT PRIMARY KEY,
  team_id          TEXT,
  actor_id         TEXT,
  action           TEXT NOT NULL,
  resource_type    TEXT NOT NULL,
  resource_id      TEXT NOT NULL,
  before_json      JSONB,
  after_json       JSONB,
  reason           TEXT,
  request_id       TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  integrity_hash   TEXT NOT NULL
);

CREATE INDEX idx_cp_audit_team_time ON cp_audit_event(team_id, created_at DESC);
CREATE INDEX idx_cp_audit_resource ON cp_audit_event(resource_type, resource_id, created_at DESC);

CREATE TABLE cp_usage_fact (
  fact_id          BIGSERIAL PRIMARY KEY,
  team_id          TEXT,
  user_id          TEXT,
  key_id           TEXT,
  model            TEXT,
  provider         TEXT,
  skill_id         TEXT,
  rag_source_id    TEXT,
  request_count    INTEGER NOT NULL DEFAULT 0,
  input_tokens     BIGINT NOT NULL DEFAULT 0,
  output_tokens    BIGINT NOT NULL DEFAULT 0,
  total_cost_usd   NUMERIC(20, 8) NOT NULL DEFAULT 0,
  error_count      INTEGER NOT NULL DEFAULT 0,
  ts_bucket        TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_cp_usage_team_bucket ON cp_usage_fact(team_id, ts_bucket DESC);
CREATE INDEX idx_cp_usage_key_bucket ON cp_usage_fact(key_id, ts_bucket DESC);
```

## 4. 迁移分期

## Phase 1: 基础治理

- 新建 cp_team/cp_user/cp_membership
- 新建 cp_virtual_key/cp_key_policy
- 将现有 key 发放逻辑双写到 cp_virtual_key

## Phase 2: 能力中心

- 新建 cp_skill/cp_skill_release
- 新建 cp_rag_source/cp_rag_sync_job
- 实现 Skill 发布回滚与 RAG 同步状态追踪

## Phase 3: 审计与报表

- 新建 cp_audit_event/cp_usage_fact
- 将关键写操作接入审计
- 构建 usage 聚合查询接口

## 5. 与现有表/内存结构对照

当前实现存在内存结构与 backend_* 表混合路径，建议迁移策略：

- 新逻辑优先落到 cp_* 表
- 旧接口继续可用但逐步改为读取 cp_* 视图
- 通过 feature flag 控制读路径切换

## 6. 数据迁移脚本结构建议（历史方案，已弃用）

```text
该目录结构为早期设计草案，当前实现已改为由后端启动阶段统一建表与演进，不再维护独立 SQL 迁移目录。
```

## 7. 回滚策略

- 所有 schema 迁移必须提供回滚 SQL
- 迁移前执行数据库快照
- 读路径切换采用灰度：team 级别逐步启用

## 8. 验收标准（数据库层）

- 可完成 key 签发、轮转、吊销并可追溯
- key 策略可限制模型和配额
- Skill 发布与回滚可查询全链路历史
- RAG 同步结果可查询且可重试
- 审计事件不可变更（只增不改）
- usage 可按 team/user/key/model 聚合
