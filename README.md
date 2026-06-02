# Aegis Nexus AI Platform

A testable Team AI platform with LiteLLM + Qdrant as the core architecture:
- AI Gateway: LiteLLM
- Knowledge Retrieval: Qdrant
- Control Plane: FastAPI governance APIs
- Closed Loop: Skill / Agent / MCP / RAG

## 架构基线与执行文档

- 主方案：docs/AI_DEVHUB_LITELLM_QDRANT_MASTER_PLAN.md
- 网关实施与接入：docs/LITELLM_GATEWAY_INTEGRATION_GUIDE.md
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

## Real Business E2E (CLI → Git → RAG → Skill → Agent → MCP)

`scripts/e2e_full_business_pipeline.sh` exercises the **entire business chain**
against a running stack: it clones a real Gitea repo, performs a CLI commit,
registers the repo with the control plane, sends an HMAC-signed `post-commit`
hook, ingests RAG knowledge, reports a task-run, applies a skill update,
performs semantic skill search, generates a RAG→Agent workflow, uploads an
MCP skill bundle, generates team rules and exports skill packs for both
`claude-code` and `opencode` targets.

### What the pipeline covers (27 assertions)

| Stage | What it validates |
| ----- | ----------------- |
| 0  | `/api/platform/runtime-health` reports `ok=true` with N models |
| 1  | CLI `git clone` + commit + push to remote `testskill.git` |
| 2  | Control-plane registers repo, `git-probe` + `git-pull` succeed **inside the backend container** |
| 3  | Rotate hook secret + report an HMAC `sha256=…` signed `post-commit` event |
| 4  | RAG ingest via `/api/evolution/gateway-knowledge/ingest` (Qdrant) |
| 5  | `task-runs/report` → `skill-updates/{id}/apply` materializes a real skill |
| 6  | Skill direct CRUD + vector-mode `/api/skills/search?query=` |
| 7  | `evolution/rag-to-skill/summarize` aggregation |
| 8  | `evolution/rag-to-agent/generate` produces an agent workflow record |
| 9  | MCP `skill-bundles/upload`, `team-rules/generate`, `apply` (dry-run), `download` |
| 10 | `/api/skills/{id}/pack/{claude-code,opencode}` artifact export |
| 11 | `evolution/overview` + `actions` ledger reflect new activity |

### Required environment

```bash
export API_BASE="http://localhost:3000"               # nginx front of backend
export ADMIN_TOKEN="sk-admin-local-change-me"         # X-Admin-Token
export GIT_REMOTE_URL="http://gitea.zodioo.com/diaojiaolou/testskill.git"
export GIT_USER="diaojiaolou"
export GIT_PASSWORD="********"                        # Gitea PAT or password
```

### Run

```bash
cd team_ai_platform
bash scripts/e2e_full_business_pipeline.sh
```

Expected tail:

```
Passed:  27
Failed:  0
All e2e business pipeline stages passed.
```

### What "MCP" means here (现状说明)

> ⚠️ **重要**：当前 commit 中 `/api/skill-sync/mcp/*` 一系列端点**只是用了 "mcp" 这个命名**，并非 Anthropic Model Context Protocol 的真实实现。它们的 handler 内部全部是 `PlatformStore` 的 CRUD（bundle / team-rules）。
>
> **目前已落地**：Git 仓库管理（后端 100%、前端 90%）、Hook HMAC 签名、RAG 摄取、Skill CRUD + 向量搜索、RAG→Agent 工作流生成、Skill Pack 导出。
>
> **尚未落地**：真实 MCP server 进程（stdio + SSE，遵循 modelcontextprotocol）、平台 → LiteLLM 模型自动同步、IDE 客户端配置生成器（cursor / claude-code / continue）、技术栈自动识别。
>
> 完整的差距分析、概念澄清与 M1–M5 落地路线图见 [`docs/ARCHITECTURE_GAP_ANALYSIS_2026-05-20.md`](docs/ARCHITECTURE_GAP_ANALYSIS_2026-05-20.md)。

### Implementation notes

- The script clones the Gitea repo into `backend/.aegis_e2e_repo/testskill`
  on the host so the backend container (which only bind-mounts `./backend`)
  can see the working tree at `/app/backend/.aegis_e2e_repo/testskill`. The
  control-plane is registered with **the container path**.
- The script is **idempotent**: it reuses a previously registered repo
  record by matching `path`, and skips git commits when the manifest is
  already up to date.
- Hook signing uses `hmac.sha256(secret, raw_body)` with header
  `X-Hook-Signature: sha256=…`; the secret is rotated to a known value
  via `POST /api/skill-sync/hooks/secret/rotate` immediately before
  the signed report so the test never depends on a pre-existing secret.

## Main Entrypoints

- Admin Console: http://localhost:8000/admin
- API Docs: http://localhost:8000/docs
- LiteLLM: http://localhost:4000/v1
- Open WebUI: http://localhost:9000
