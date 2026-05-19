# Aegis Nexus AI Platform

A testable Team AI platform with LiteLLM + Qdrant as the core architecture:
- AI Gateway: LiteLLM
- Knowledge Retrieval: Qdrant
- Control Plane: FastAPI governance APIs
- Closed Loop: Skill / Agent / MCP / RAG

## 架构基线与执行文档

- 主方案：docs/AI_DEVHUB_LITELLM_QDRANT_MASTER_PLAN.md
- 文档索引：docs/DOCS_INDEX.md
- 历史归档：docs/archive/2026-05-19/

## Quick Start

1. Prepare env file:

```bash
cd team_ai_platform
cp .env.example .env
```

2. Fill provider keys in `.env` (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, etc.).
	If `open_webui` image pull fails, set `OPEN_WEBUI_IMAGE=ghcr.io/open-webui/open-webui:latest`.

3. Start services:

```bash
bash scripts/start.sh
```

## 每次开发完成后的 Docker 验证（推荐）

在 `team_ai_platform` 下执行：

```bash
bash scripts/dev_build_and_up.sh
```

该脚本会固定执行：
- 使用工作区根目录 `.venv` 运行后端测试
- 在 `frontend` 目录执行 `npm run build`
- 执行 `docker compose up -d --build`

常用参数：

```bash
# 只做前端 build + docker 重建，不跑后端测试
bash scripts/dev_build_and_up.sh --skip-tests

# 不重建镜像，仅启动现有容器
bash scripts/dev_build_and_up.sh --skip-compose-build
```

## Testable Delivery Path

Run the full runtime acceptance pipeline:

```bash
cd team_ai_platform
source ../.venv/bin/activate
export TEAM_AI_PLATFORM_ADMIN_TOKEN=your-admin-token
export LITELLM_MASTER_KEY=sk-team-master-change-me
bash scripts/e2e_runtime_pipeline.sh
```

Pipeline checks:
- Backend health
- Runtime config preview/apply

---

# 目录结构

- backend/  —— FastAPI + SQLModel 后端，见 app/
- frontend/ —— React + Ant Design Pro/Vite 前端

# 启动开发环境

## 后端
1. 进入 backend 目录，创建虚拟环境并安装依赖：
	```bash
	cd backend
	python -m venv .venv
	source .venv/bin/activate
	pip install -r requirements.txt
	```
2. 启动 FastAPI 服务：
	```bash
	uvicorn app.main:app --reload
	```

## 前端
1. 进入 frontend 目录，安装依赖：
	```bash
	cd frontend
	npm install
	npm run dev
	```

# 主要功能模块（当前主线）
- 控制台（AI 治理指标）
- 虚拟密钥、模型注册、AI 服务商
- 技能平台、智能体、治理中心、观测中心
- 知识库（RAG）与代码仓库（Skill 同步来源）

# 测试
- 后端接口：访问 http://localhost:8000/docs 查看所有API
- 前端页面：访问 http://localhost:5173

---
如需补充功能或遇到问题，请联系开发负责人。
- LiteLLM restart and health
- `/v1/models` check
- virtual key generation and `/v1/chat/completions` probe

By default, chat probe upstream errors are non-blocking (useful when provider keys are not fully configured).
Set `E2E_REQUIRE_CHAT_SUCCESS=1` to enforce strict chat success.

Reports are written to `reports/`.

## Continuous Delivery Check

GitHub Actions workflow is provided at `.github/workflows/ci-runtime-delivery.yml`.
It validates:
- shell script syntax
- runtime control-plane tests
- Docker Compose configuration render

This workflow runs on each push to `main` and on every pull request.

## Fast Local Validation

```bash
cd team_ai_platform
source ../.venv/bin/activate
bash -n scripts/apply_litellm_gateway.sh scripts/e2e_runtime_pipeline.sh
pytest -q backend/tests/test_runtime_config.py backend/tests/test_control_plane_v2.py
```

## Main Entrypoints

- Admin Console: http://localhost:8000/admin
- API Docs: http://localhost:8000/docs
- LiteLLM: http://localhost:4000/v1
- Open WebUI: http://localhost:9000
