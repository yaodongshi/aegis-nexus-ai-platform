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
- Scripted startup and health verification

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
bash scripts/start.sh
```

1. Verify service health.

```bash
bash scripts/healthcheck.sh
```

### 6. Access endpoints

- LiteLLM API: `http://localhost:4000/v1`
- Open WebUI: `http://localhost:3000`
- Qdrant: `http://localhost:6333`

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
- 提供一键启动与健康检查脚本

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
bash scripts/start.sh
```

1. 执行健康检查。

```bash
bash scripts/healthcheck.sh
```

### 6. 访问地址

- LiteLLM API: `http://localhost:4000/v1`
- Open WebUI: `http://localhost:3000`
- Qdrant: `http://localhost:6333`

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
