# Team AI Platform 用户手册（V2）

> 对齐声明（2026-05-19）：当前架构基线为 LiteLLM + Qdrant 闭环；产品与架构总设计请先阅读 `AI_DEVHUB_LITELLM_QDRANT_MASTER_PLAN.md`，本文档作为操作手册补充。

> 版本：v2.0 · 适用于 2026-05-14 及以后主线

---

## 目录
1. [系统架构与核心概念](#1-系统架构与核心概念)
2. [快速部署与环境变量](#2-快速部署与环境变量)
3. [团队与成员管理](#3-团队与成员管理)
4. [虚拟 Key 与策略管理（V2 控制面）](#4-虚拟-key-与策略管理v2-控制面)
5. [主流客户端对接方式](#5-主流客户端对接方式)
6. [常见问题与排查](#6-常见问题与排查)
7. [方案 A 完整设计文档](#7-方案-a-完整设计文档)
8. [开发验证（V2 控制面）](#8-开发验证v2-控制面)

---

## 1. 系统架构与核心概念

- **控制面（Control Plane）**：负责团队、成员、虚拟 Key、策略、审计等治理能力，API 路径 `/api/v1/*`。
- **数据面（Data Plane）**：统一模型网关（LiteLLM/Portkey/OpenRouter等），API 路径 `/v1/*`，兼容 OpenAI/Anthropic/Google Gemini 等主流协议。
- **虚拟 Key**：团队管理员为成员分发的访问凭证，支持精细化策略（模型白名单、配额、速率、紧急封禁等）。
- **Key Policy**：绑定到虚拟 Key 的访问控制策略，支持热更新。
- **多团队/多租户**：每个团队独立隔离，支持企业级分权。

---

## 2. 快速部署与环境变量

1. **环境变量配置**（`.env`）：
   - `TEAM_AI_PLATFORM_ADMIN_TOKEN`：平台管理员 Token
   - `TEAM_AI_PLATFORM_DB_DSN`：PostgreSQL 连接串
   - `TEAM_AI_PLATFORM_LITELLM_MASTER_KEY`：LiteLLM 网关主控 Key
  - `TEAM_AI_PLATFORM_OBSERVABILITY_BACKEND`：观测后端（`langfuse`/`helicone`/`none`，默认 `langfuse`）
  - `LANGFUSE_PUBLIC_KEY`、`LANGFUSE_SECRET_KEY`、`LANGFUSE_HOST`（使用 Langfuse 时）
  - `HELICONE_API_KEY`、`HELICONE_BASE_URL`（使用 Helicone 时）
2. **启动服务**：
   ```bash
   docker compose up -d
   # 或本地开发
   source .venv/bin/activate
   uvicorn team_ai_platform.backend.app.main:app --reload
   ```
3. **初始化数据库**：
  ```bash
  # 启动后端后会自动创建控制面所需核心表（如 cp_virtual_keys / cp_key_policies）
  # 如需手动验证，可连接数据库查看表是否存在
  psql "$TEAM_AI_PLATFORM_DB_DSN" -c "\dt cp_*"
  ```

---

## 3. 团队与成员管理

- **创建团队**：
  ```bash
  curl -X POST http://localhost:8000/api/v1/teams \
    -H "X-Admin-Token: ..." \
    -d '{"name": "AI研发组"}'
  ```
- **添加成员**：
  ```bash
  curl -X POST http://localhost:8000/api/v1/teams/{team_id}/members \
    -H "X-Admin-Token: ..." \
    -d '{"user_id": "u_zhangsan", "role": "member"}'
  ```
- **查询团队/成员**：
  ```bash
  curl http://localhost:8000/api/v1/teams?limit=20
  curl http://localhost:8000/api/v1/teams/{team_id}/members
  ```

---

## 4. 虚拟 Key 与策略管理（V2 控制面）

### 4.1 创建虚拟 Key
```bash
curl -X POST http://localhost:8000/api/v1/keys \
  -H "X-Admin-Token: ..." \
  -d '{
    "team_id": "team_xxx",
    "owner_type": "user",
    "owner_id": "u_zhangsan",
    "alias": "张三开发Key",
    "expires_at": "2026-06-30T00:00:00Z"
  }'
```
返回：`key.key_id`、`key.key_secret`（仅创建时可见）

### 4.2 配置 Key 策略
```bash
curl -X PUT http://localhost:8000/api/v1/policies/keys/{key_id} \
  -H "X-Admin-Token: ..." \
  -d '{
    "allowed_models": ["gpt-4.1", "claude-sonnet-4"],
    "quota_tokens_day": 100000,
    "rate_limit_rpm": 60
  }'
```

### 4.3 查询/撤销/轮换 Key
```bash
# 查询
curl http://localhost:8000/api/v1/keys?team_id=team_xxx
# 撤销
curl -X POST http://localhost:8000/api/v1/keys/{key_id}/revoke -H "X-Admin-Token: ..."
# 轮换
curl -X POST http://localhost:8000/api/v1/keys/{key_id}/rotate -H "X-Admin-Token: ..."
```

---

## 5. 主流客户端对接方式

### 5.1 OpenAI/Anthropic/Claude/Gemini 兼容 SDK
- `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`：使用虚拟 Key
- `OPENAI_BASE_URL`/`ANTHROPIC_BASE_URL`：`http://localhost:4000/v1`

### 5.2 CLI 工具
```bash
export OPENAI_API_KEY="sk-v2-xxxx"
export OPENAI_BASE_URL="http://localhost:4000/v1"
codex "写一个冒泡排序"
```

### 5.3 Open WebUI
- 直接登录，无需手动配置 Key，后台自动路由

### 5.4 OpenCode
- 配置 `baseURL` 和 `apiKey` 指向团队网关

---

## 6. 常见问题与排查

**Q1：新 Key/策略不生效？**
- 检查控制面 `/api/v1/keys`、`/api/v1/policies/keys/{key_id}` 返回内容
- 检查 LiteLLM 网关是否热加载最新配置

**Q2：团队成员无法访问模型？**
- 检查 Key 策略的 allowed_models 是否包含目标模型
- 检查 Key 状态是否为 active

**Q3：如何审计 Key 使用记录？**
- 访问 `/api/v1/keys/{key_id}/audit-log` 查看操作与调用历史

**Q4：如何回滚/升级数据库？**
- 当前版本不再维护独立 SQL 迁移目录；结构变更通过后端版本升级与启动时建表逻辑统一管理

---

## 7. 方案 A 完整设计文档

- 推荐方案（LiteLLM + Langfuse + 自研控制面）的完整架构设计请参考：
  - `docs/SOLUTION_A_COMPLETE_DESIGN.md`
- OpenSpec 变更包（proposal/design/tasks/spec deltas）请参考：
  - `openspec/changes/update-solution-a-complete-design/`

---

## 8. 开发验证（V2 控制面）

1. 安装后端依赖：
  ```bash
  source /Users/yaodongshi/Documents/develop/odoo/odoo19ee/.venv/bin/activate
  pip install -r backend/requirements.txt
  ```
2. 运行 V2 控制面测试：
  ```bash
  pytest -q backend/tests/test_control_plane_v2.py
  ```
3. 预览并导出 LiteLLM 运行时配置（由控制面状态确定性生成）：
  ```bash
  # 预览配置
  curl -s http://localhost:8000/api/v1/runtime/litellm-config \
    -H "X-Admin-Token: ${TEAM_AI_PLATFORM_ADMIN_TOKEN}"

  # 导出到默认目录（team_ai_platform/litellm）
  curl -s -X POST http://localhost:8000/api/v1/runtime/litellm-config/apply \
    -H "X-Admin-Token: ${TEAM_AI_PLATFORM_ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{}'
  ```
   导出的 `litellm/config.yaml` 会在观测变量满足时自动包含对应 callback：
   - Langfuse: `success_callback: [langfuse]`
   - Helicone: `success_callback: [helicone]`
   
  也可直接执行统一脚本（内部会先调用 `/api/v1/runtime/litellm-config/apply`，再重启 LiteLLM）：
  ```bash
  export TEAM_AI_PLATFORM_ADMIN_TOKEN=your-admin-token
  bash scripts/apply_litellm_gateway.sh
  ```
4. 通过标准：
  - `6 passed`（创建/查询/撤销/轮换/策略与鉴权路径）

---

*如需完整 API 说明，访问 http://localhost:8000/docs* （Swagger 自动生成）

---

> 本文档最后更新：2026-05-14
