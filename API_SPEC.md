# Aegis Nexus AI Platform API Spec

> 说明：本文档给出平台控制面的核心接口草案。用户侧仍以 ccswitch / Claude Code / Codex / OpenCode 等 OpenAI-compatible 客户端接入统一网关。

## 1. 通用约定

### 1.1 鉴权

- 用户请求使用 `Authorization: Bearer <virtual_key>`
- 管理类接口使用管理员会话或后端服务身份
- 所有写操作应支持幂等键或业务唯一标识

### 1.2 通用错误码

- `401 Unauthorized`：Key 缺失或无效
- `403 Forbidden`：权限不足或策略拒绝
- `404 Not Found`：资源不存在
- `409 Conflict`：版本冲突、重复发布、状态不允许
- `429 Too Many Requests`：配额或频率限制触发
- `500 Internal Server Error`：网关或后端内部异常

### 1.3 返回风格

- 成功返回 JSON
- 列表接口默认支持分页、过滤、排序
- 时间统一使用 ISO 8601 / UTC

## 2. 模型目录 API

### GET /api/models

返回当前平台可见模型列表。

响应字段：

- `id`：模型唯一标识
- `provider`：上游供应商
- `name`：模型名称
- `endpoint`：上游调用地址
- `context_window`：上下文长度
- `cost_tier`：成本等级
- `availability`：当前可用状态
- `tags`：业务标签
- `labels`：团队或场景标签

示例：

```json
[
  {
    "id": "gpt-4o",
    "provider": "openai",
    "name": "GPT-4o",
    "endpoint": "https://api.openai.com/v1/chat/completions",
    "context_window": 128000,
    "cost_tier": "high",
    "availability": "active",
    "tags": ["chat", "code"],
    "labels": {"team": "platform", "tier": "prod"}
  }
]
```

### POST /api/models/register

注册模型元数据。

请求字段：

- `provider`
- `name`
- `endpoint`
- `context_window`
- `cost_tier`
- `tags`
- `labels`
- `quota`

### GET /api/models/{id}

查询单个模型详情。

### PATCH /api/models/{id}

更新模型元数据或可用状态。

## 3. Key 管理 API

### POST /api/keys/issue

颁发虚拟 Key。

请求字段：

- `user_id`
- `project_id`
- `scope`
- `expire_at`
- `quota`

响应字段：

- `key_id`
- `key_secret`
- `status`
- `expire_at`

示例：

```json
{
  "request": {
    "user_id": "u_1001",
    "project_id": "p_ai_platform",
    "scope": "project:read,project:write",
    "expire_at": "2026-12-31T23:59:59Z",
    "quota": 100000
  },
  "response": {
    "key_id": "key_01HXYZ...",
    "key_secret": "sk-virtual-9a8b7c6d5e4f",
    "status": "active",
    "expire_at": "2026-12-31T23:59:59Z"
  }
}
```

### GET /api/keys

查询 Key 列表。

### DELETE /api/keys/{id}

回收或禁用 Key。

## 4. 技能包 API

### GET /api/skills

查询技能包列表。

### POST /api/skills/publish

发布技能包。

请求字段：

- `package_name`
- `version`
- `skill_yaml`
- `policy_json`
- `tests_archive`

响应字段：

- `skill_id`
- `version`
- `lifecycle_status`

示例：

```json
{
  "request": {
    "package_name": "code-security-scan",
    "version": "1.0.0",
    "skill_yaml": "name: code-security-scan\nversion: 1.0.0\ndescription: Security scanning skill",
    "policy_json": "{\"allowed_actions\":[\"read\",\"analyze\"]}",
    "tests_archive": "<binary-archive-base64>"
  },
  "response": {
    "skill_id": "skill_01HABC...",
    "version": "1.0.0",
    "lifecycle_status": "dev"
  }
}
```

### GET /api/skills/{id}

查询技能包详情。

### POST /api/skills/{id}/rollback

回滚到历史版本。

## 5. 会话与记忆 API

### GET /api/sessions

查询会话列表。

### GET /api/sessions/{id}

查询单个会话详情。

### POST /api/sessions

创建新会话。

### PATCH /api/sessions/{id}

更新会话内容或状态。

## 6. 策略与审批 API

### GET /api/policies

查询所有策略。

### POST /api/policies

新增或更新策略。

### POST /api/approvals/submit

提交审批请求。

请求字段：

- `applicant_id`
- `action`
- `resource_id`
- `reason`

响应字段：

- `approval_id`
- `status`
- `approver_id`

示例：

```json
{
  "request": {
    "applicant_id": "u_1001",
    "action": "db_migrate",
    "resource_id": "db-prod",
    "reason": "release hotfix"
  },
  "response": {
    "approval_id": "appr_01HJKL...",
    "status": "pending",
    "approver_id": null
  }
}
```

### GET /api/approvals/{id}

查询审批进度。
