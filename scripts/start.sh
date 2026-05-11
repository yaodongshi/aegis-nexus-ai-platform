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

echo "[INFO] Starting Team AI Platform stack..."
docker compose up -d

echo "[INFO] Services started."
echo "[INFO] LiteLLM endpoint: http://localhost:4000/v1"
echo "[INFO] Open WebUI: http://localhost:3000"
echo "[INFO] Qdrant: http://localhost:6333"
