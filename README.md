# Aegis Nexus AI Platform

中文名: 天枢智枢协同智能平台

Team-grade AI infrastructure that unifies model access, key governance, and knowledge-ready architecture while preserving developers' existing tools.

企业级 AI 协作底座，统一模型接入与密钥治理，并保留团队既有开发工具与工作习惯。

完整最新版方案请查看 [TEAM_AI_PLATFORM_FULL_VERSION.md](TEAM_AI_PLATFORM_FULL_VERSION.md)。

## EN

### 1. Overview

Aegis Nexus AI Platform is an internal team AI backbone built with open-source components. It provides one OpenAI-compatible endpoint for multiple model providers, a shared web workspace, and a vector database foundation for future RAG and multi-agent workflows.

### 2. Core capabilities (Phase 1 MVP)

- Unified model gateway via LiteLLM (`/v1` OpenAI-compatible API)
- Shared team UI via Open WebUI
- Qdrant vector store as RAG-ready data plane
- PostgreSQL metadata layer for gateway policy/state
- Virtual key bootstrap for team/project level access governance
- Docker Compose one-command startup and health verification

### 3. Architecture

1. Developer tools call one endpoint: `http://localhost:4000/v1`
2. LiteLLM routes requests to configured providers/models
3. Open WebUI uses the same endpoint for team collaboration
4. Qdrant is available for knowledge indexing and retrieval services

### 4. Tech stack

- LiteLLM
- Open WebUI
- Qdrant
- PostgreSQL 16
- Docker Compose

### 5. Quick start

1. Prepare environment variables.

```bash
cd team_ai_platform
cp .env.example .env
```

1. Fill provider keys and gateway settings in `.env`.
1. Start all services.

```bash
docker compose up -d --build
```

If image pull is slow or unstable, you can set mirror images in `.env`:

```dotenv
LITELLM_DB_IMAGE=postgres:16
QDRANT_IMAGE=qdrant/qdrant:latest
DOCKER_CLIENT_TIMEOUT=180
COMPOSE_HTTP_TIMEOUT=180
```

1. Verify service health.

```bash
docker compose ps
curl -fsS http://localhost:8000/health
```

### 6. Access endpoints

- LiteLLM API: `http://localhost:4000/v1`
- Open WebUI: `http://localhost:9000`
- Qdrant: `http://localhost:6333`
- Backend API docs: `http://localhost:8000/docs`
- Provider Console UI: `http://localhost:8000/provider-console`

### 6.1 Provider management on Web

Use Web APIs (Swagger UI) to manage providers instead of editing provider config files manually:

1. Open `http://localhost:8000/docs`
1. Call `GET /api/providers/presets` to view preset templates
1. Call `POST /api/providers` to add provider (name/base_url/api_key/apps)
1. Call `POST /api/providers/{provider_id}/discover-models` to auto-fetch `/v1/models`
1. Call `POST /api/providers/{provider_id}/sync` to sync as unified provider

### 7. Generate a virtual key

```bash
cd team_ai_platform
export LITELLM_MASTER_KEY=sk-team-master-change-me
bash scripts/bootstrap_virtual_key.sh
```

Use virtual keys for users/projects instead of distributing upstream provider keys.

### 8. Client integration

- OpenAI-compatible clients:
  - Base URL: `http://localhost:4000/v1`
  - API key: virtual key (recommended)
- Claude Code / Codex / OpenCode / similar wrappers:
  - Prefer OpenAI-compatible endpoint mode
  - Avoid local provider key sprawl where possible

### 9. Security baseline

- Never commit `.env`
- Rotate `LITELLM_MASTER_KEY` periodically
- Scope and revoke virtual keys by team/project lifecycle
- Upgrade to IdP + short-lived tokens + Vault/KMS in Phase 2

### 10. Roadmap

- Phase 2:
  - Observability and tracing (Langfuse/OpenTelemetry)
  - Knowledge ingestion pipeline (Git/Wiki/Confluence)
  - Prompt/Skill GitOps pipeline
- Phase 3:
  - Multi-agent orchestration
  - Approval gates for high-risk actions
  - Evaluation-driven governance loop

## 中文

### 1. 项目概述

天枢智枢协同智能平台是面向团队内部的 AI 协作底座。平台以开源组件为核心，实现统一模型网关、团队共享入口与向量知识底座，为后续 RAG 与多 Agent 编排打好基础。

### 2. 当前能力（Phase 1 MVP）

- 基于 LiteLLM 的统一模型网关（兼容 OpenAI API）
- 基于 Open WebUI 的团队共享入口
- 基于 Qdrant 的向量数据库底座（RAG Ready）
- 基于 PostgreSQL 的网关元数据与策略存储
- 支持虚拟 Key 初始化，便于团队级权限治理
- 提供基于 Docker Compose 的一键启动与健康检查

### 3. 架构说明

1. 开发工具统一访问 `http://localhost:4000/v1`
2. LiteLLM 按模型路由到不同上游供应商
3. Open WebUI 复用同一网关进行团队协作
4. Qdrant 预留知识入库与检索服务能力

### 4. 技术栈

- LiteLLM
- Open WebUI
- Qdrant
- PostgreSQL 16
- Docker Compose

### 5. 快速开始

1. 准备环境变量文件。

```bash
cd team_ai_platform
cp .env.example .env
```

1. 在 `.env` 中填写各模型供应商密钥与网关参数。
1. 启动服务。

```bash
docker compose up -d --build
```

如果镜像拉取不稳定（例如 `registry-1.docker.io` 超时），可在 `.env` 设置镜像与超时参数：

```dotenv
LITELLM_DB_IMAGE=postgres:16
QDRANT_IMAGE=qdrant/qdrant:latest
DOCKER_CLIENT_TIMEOUT=180
COMPOSE_HTTP_TIMEOUT=180
```

1. 执行健康检查。

```bash
docker compose ps
curl -fsS http://localhost:8000/health
```

### 6. 访问地址

- LiteLLM API: `http://localhost:4000/v1`
- Open WebUI: `http://localhost:9000`
- Qdrant: `http://localhost:6333`
- Backend API 文档: `http://localhost:8000/docs`
- Provider Console 页面: `http://localhost:8000/provider-console`

### 6.1 在 Web 上管理供应商

可通过 Web API（Swagger UI）管理供应商，不再手改供应商配置文件：

1. 打开 `http://localhost:8000/docs`
1. 调用 `GET /api/providers/presets` 查看预设模板
1. 调用 `POST /api/providers` 新增供应商（名称/端点/API Key/应用绑定）
1. 调用 `POST /api/providers/{provider_id}/discover-models` 自动获取 `/v1/models`
1. 调用 `POST /api/providers/{provider_id}/sync` 作为统一供应商同步到目标应用

### 7. 生成虚拟 Key

```bash
cd team_ai_platform
export LITELLM_MASTER_KEY=sk-team-master-change-me
bash scripts/bootstrap_virtual_key.sh
```

建议按用户/项目发放虚拟 Key，避免分发上游厂商原始密钥。

### 8. 客户端接入建议

- OpenAI 兼容客户端:
  - Base URL: `http://localhost:4000/v1`
  - API Key: 虚拟 Key（推荐）
- Claude Code / Codex / OpenCode 等:
  - 优先使用 OpenAI 兼容网关模式
  - 尽量避免本地分散维护多厂商密钥

### 9. 安全基线

- 严禁提交 `.env`
- 定期轮换 `LITELLM_MASTER_KEY`
- 按团队/项目生命周期回收虚拟 Key
- Phase 2 升级到 IdP + 短期令牌 + Vault/KMS

### 10. 路线图

- Phase 2:
  - 观测与追踪（Langfuse/OpenTelemetry）
  - 知识入库流水线（Git/Wiki/Confluence）
  - Prompt/Skill GitOps 管理
- Phase 3:
  - 多 Agent 编排
  - 高风险操作审批网关
  - 评测驱动治理闭环
