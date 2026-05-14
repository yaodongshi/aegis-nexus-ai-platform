#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
  echo "[ERROR] Missing .env file in ${PROJECT_ROOT}" >&2
  echo "[INFO] Copy .env.example to .env and fill in provider keys." >&2
  exit 1
fi

cd "${PROJECT_ROOT}"

OPEN_WEBUI_PORT="${OPEN_WEBUI_PORT:-9000}"

echo "[INFO] Starting Team AI Platform stack..."
docker compose up -d

echo "[INFO] Services started."
echo "[INFO] Team AI Admin Console: http://localhost:8000/admin"
echo "[INFO] Backend API docs: http://localhost:8000/docs"
echo "[INFO] Team workspace (Open WebUI): http://localhost:${OPEN_WEBUI_PORT}"
echo "[INFO] LiteLLM gateway: http://localhost:4000/v1"
echo "[INFO] Qdrant vector store: internal service on http://localhost:6333"
echo "[INFO] Apply gateway changes after provider updates: bash scripts/apply_litellm_gateway.sh"
echo "[INFO] Minimal verification: bash scripts/healthcheck.sh"
