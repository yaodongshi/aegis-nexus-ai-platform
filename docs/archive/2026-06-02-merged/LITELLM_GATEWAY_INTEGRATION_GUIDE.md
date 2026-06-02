# LiteLLM Gateway 实施与接入指南

本文档用于统一 Team AI Platform 的网关落地流程，覆盖环境变量、启动、配置应用和最小可用验证。

## 1. 环境变量准备

1. 复制模板：

```bash
cd team_ai_platform
cp .env.example .env
```

2. 至少填写以下关键项：

```env
LITELLM_MASTER_KEY=sk-team-master-change-me
LITELLM_SALT_KEY=sk-team-salt-change-me
OPENAI_API_KEY=your-openai-key
TEAM_AI_PLATFORM_ADMIN_TOKEN=your-admin-token
TEAM_AI_PLATFORM_GATEWAY_API_KEY=${LITELLM_MASTER_KEY}
```

3. 可选观测配置（仅在需要时）：

```env
TEAM_AI_PLATFORM_OBSERVABILITY_BACKEND=none
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=
HELICONE_API_KEY=
HELICONE_BASE_URL=
```

## 2. 启动系统

```bash
cd team_ai_platform
bash scripts/start.sh
```

启动后默认入口：
- Admin: http://localhost:8000/admin
- API Docs: http://localhost:8000/docs
- LiteLLM: http://localhost:4000/v1
- Open WebUI: http://localhost:9000

## 3. 应用网关配置

每次供应商配置变更后，执行：

```bash
cd team_ai_platform
bash scripts/apply_litellm_gateway.sh
```

只检查当前网关模型列表：

```bash
cd team_ai_platform
bash scripts/apply_litellm_gateway.sh check
```

仅同步模型到网关数据库（不重启）：

```bash
cd team_ai_platform
bash scripts/apply_litellm_gateway.sh sync
```

## 4. 最小可用验证

```bash
cd team_ai_platform
bash scripts/healthcheck.sh
```

建议追加两条直连校验：

```bash
curl -s http://localhost:4000/health | cat
curl -s http://localhost:4000/v1/models -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" | cat
```

## 5. 常见问题

1. `/v1/models` 返回 401：
- 检查 `LITELLM_MASTER_KEY` 是否与请求 Header 一致。

2. `docker compose config` 出现大量空变量警告：
- 属于未配置供应商 key 的预期行为，不影响基础启动。
- 如需消除警告，可在 `.env` 中补齐对应变量。

3. 网关模型未刷新：
- 先执行 `bash scripts/apply_litellm_gateway.sh`。
- 再执行 `bash scripts/apply_litellm_gateway.sh check` 观察模型列表。

## 6. 交付基线

当前基线已落地：
- `litellm/config.yaml` 提供默认模型、路由和回退策略。
- `.env.example` 补齐网关和观测相关关键变量。
- 启动脚本具备关键变量缺失告警。
- 网关应用与健康检查脚本可直接用于日常运维。
