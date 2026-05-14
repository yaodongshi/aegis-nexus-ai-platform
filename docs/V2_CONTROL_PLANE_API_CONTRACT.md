# Aegis Nexus V2 控制面 API 契约

> 文档定位：V2 进入后端实施阶段的接口基线。
> 
> 数据平面继续由 LiteLLM 提供统一模型调用能力，控制面负责用户、团队、虚拟 Key、模型授权、Skill/RAG 注册与治理。

## 1. 设计原则

- 客户端接入契约稳定：前端工具统一使用 OpenAI-compatible 网关入口
- 控制面与数据面解耦：控制面只做身份、策略、发布、审计
- 所有写接口可审计：必须写入 audit_event
- 所有关键资源支持软删除/禁用，避免硬删造成追溯断裂

## 2. API 分层

- 控制面管理 API：`/api/v1/*`
- 数据面调用 API：`/v1/*`（由 LiteLLM/网关提供）
- 能力调用 API：`/v1/capabilities/*`（由控制面授权、运行时执行）

## 3. 鉴权与身份

### 3.1 鉴权模式

- 管理 API：`Authorization: Bearer <admin_session_or_service_token>`
- 用户级管理 API：`Authorization: Bearer <user_session_token>`
- 数据面调用：`Authorization: Bearer <virtual_key>`

### 3.2 标准身份头

- `X-User-Id`
- `X-Team-Id`
- `X-Request-Id`
- `X-Client-App`（可选：claude/codex/gemini/opencode/hermes/custom）

## 4. 统一响应结构

### 4.1 成功响应

```json
{
  "request_id": "req_01J...",
  "data": {},
  "meta": {
    "ts": "2026-05-14T12:00:00Z"
  }
}
```

### 4.2 分页响应

```json
{
  "request_id": "req_01J...",
  "data": {
    "items": [],
    "total": 0,
    "limit": 20,
    "offset": 0
  },
  "meta": {
    "ts": "2026-05-14T12:00:00Z"
  }
}
```

### 4.3 错误响应

```json
{
  "request_id": "req_01J...",
  "error": {
    "code": "POLICY_DENIED",
    "message": "model is not allowed for current virtual key",
    "details": {
      "model": "claude-sonnet-4"
    }
  }
}
```

## 5. 控制面核心接口

## 5.1 Team / User

### POST /api/v1/teams

创建团队。

请求字段：
- `name`
- `slug`
- `owner_user_id`

### GET /api/v1/teams

分页查询团队。

### POST /api/v1/teams/{team_id}/members

新增团队成员。

请求字段：
- `user_id`
- `role`（owner/admin/member/auditor）

### PATCH /api/v1/teams/{team_id}/members/{user_id}

变更成员角色或状态。

## 5.2 Virtual Key 生命周期

### POST /api/v1/keys

签发虚拟 Key。

请求字段：
- `team_id`
- `alias`
- `owner_type`（user/project/service）
- `owner_id`
- `expires_at`
- `quota_tokens`
- `rate_limit_rpm`

响应字段：
- `key_id`
- `key_secret`（仅首次返回）
- `status`

### GET /api/v1/keys

按 team/owner/status 分页查询。

### POST /api/v1/keys/{key_id}/rotate

轮转虚拟 Key，旧 Key 可配置宽限期。

### POST /api/v1/keys/{key_id}/revoke

立即吊销。

### GET /api/v1/keys/{key_id}/usage

查询 key 维度用量（token/requests/cost/error_rate）。

## 5.3 模型授权与策略

### PUT /api/v1/policies/keys/{key_id}/models

配置可用模型白名单。

请求字段：
- `allowed_models`（数组）
- `denied_models`（可选）

### PUT /api/v1/policies/keys/{key_id}/quota

配置配额与限流。

请求字段：
- `quota_tokens_day`
- `quota_tokens_month`
- `rate_limit_rpm`
- `burst_limit`

### POST /api/v1/policies/emergency-block

紧急封禁 key/model/skill/source。

请求字段：
- `resource_type`（key/model/skill/rag_source）
- `resource_id`
- `reason`
- `duration_seconds`（可选）

## 5.4 Skill Registry

### POST /api/v1/skills

注册技能包。

请求字段：
- `name`
- `version`
- `owner_scope`（team/project/global）
- `manifest`
- `policy`
- `signature`

### GET /api/v1/skills

按 scope/channel/status 查询。

### POST /api/v1/skills/{skill_id}/release

发布到渠道。

请求字段：
- `channel`（dev/stage/prod）
- `rollout_percent`

### POST /api/v1/skills/{skill_id}/rollback

回滚到指定版本或上一个稳定版本。

## 5.5 RAG Source Registry

### POST /api/v1/rag/sources

注册数据源。

请求字段：
- `name`
- `connector_type`（git/wiki/confluence/s3/http/custom）
- `scope`
- `config`
- `sync_policy`

### GET /api/v1/rag/sources

查询数据源列表。

### POST /api/v1/rag/sources/{source_id}/sync

触发手动同步。

### GET /api/v1/rag/sources/{source_id}/status

查询最近同步状态与快照版本。

## 5.6 审计与报表

### GET /api/v1/audit/events

按 actor/resource/action/time 查询审计事件。

### GET /api/v1/reports/usage

按 team/user/key/model/skill 维度聚合统计。

## 6. 数据面与能力面契约

## 6.1 POST /v1/chat/completions

- 保持 OpenAI 兼容
- 控制面前置校验：key 状态、模型授权、配额、限流
- 拒绝时返回标准错误码：`POLICY_DENIED`、`QUOTA_EXCEEDED`、`KEY_REVOKED`

## 6.2 POST /v1/responses

- 同上，兼容 responses 路径

## 6.3 POST /v1/capabilities/{name}/invoke

- 控制面做 scope 和 channel 授权
- 记录 capability 调用审计和成本归因

请求字段：
- `input`
- `context`
- `session_id`
- `project_id`

## 7. 错误码清单（V2）

- `UNAUTHORIZED`
- `FORBIDDEN`
- `POLICY_DENIED`
- `KEY_REVOKED`
- `KEY_EXPIRED`
- `QUOTA_EXCEEDED`
- `RATE_LIMITED`
- `RESOURCE_NOT_FOUND`
- `RESOURCE_CONFLICT`
- `INVALID_ARGUMENT`
- `UPSTREAM_UNAVAILABLE`
- `INTERNAL_ERROR`

## 8. 最小验收清单（接口层）

- 管理端可签发、轮转、吊销 key
- key 级模型白名单可即时生效
- Skill 可注册、发布、回滚
- RAG 数据源可注册、同步、查状态
- 所有写操作可在 `/api/v1/audit/events` 查询到
- `/v1/chat/completions` 在策略拒绝时返回可机器识别错误码

## 9. 与现有实现的映射建议

当前后端已有路由基础（keys/models/skills/policies/providers/approvals/sessions），建议以不破坏现状方式迭代：

- 先保留现有 `/api/*` 路径并增加 `/api/v1/*` 新版本
- 在 store 层引入正式实体表，再逐步替换内存结构
- 先实现 key 与 policy 联动，再接 skill/rag 注册能力
