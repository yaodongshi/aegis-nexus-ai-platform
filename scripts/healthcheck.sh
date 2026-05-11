#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${1:-http://localhost:8000/health}"
LITELLM_URL="${2:-http://localhost:4000/health}"
WEBUI_URL="${3:-http://localhost:3000/health}"
QDRANT_URL="${4:-http://localhost:6333/healthz}"

echo "[INFO] Checking backend..."
curl -sS "${BACKEND_URL}" | cat

echo "[INFO] Checking LiteLLM..."
curl -sS "${LITELLM_URL}" | cat

echo ""
echo "[INFO] Checking Open WebUI..."
curl -sS "${WEBUI_URL}" | cat || true

echo ""
echo "[INFO] Checking Qdrant..."
curl -sS "${QDRANT_URL}" | cat

echo ""
echo "[INFO] Health checks completed."
