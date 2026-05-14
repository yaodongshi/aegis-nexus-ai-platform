# Aegis Nexus AI Platform

A testable Team AI platform based on Solution A:
- Data plane: LiteLLM gateway
- Observability plane: Langfuse/Helicone profile injection
- Control plane: FastAPI governance APIs

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
