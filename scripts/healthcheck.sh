#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${1:-http://localhost:8000/health}"
LITELLM_URL="${2:-http://localhost:4000/health}"
WEBUI_URL="${3:-http://localhost:9000/health}"
QDRANT_URL="${4:-http://localhost:6333/healthz}"

echo "[INFO] Checking backend..."
curl -sS "${BACKEND_URL}" | cat

echo "[INFO] Admin console entrypoint: http://localhost:8000/admin"

echo "[INFO] Checking LiteLLM..."
if [[ -n "${LITELLM_MASTER_KEY:-}" ]]; then
	curl -sS "${LITELLM_URL}" \
		-H "Authorization: Bearer ${LITELLM_MASTER_KEY}" | cat
else
	LITELLM_STATUS_CODE=$(curl -sS -o /tmp/team_ai_litellm_health.out -w "%{http_code}" "${LITELLM_URL}")
	if [[ "${LITELLM_STATUS_CODE}" == "200" || "${LITELLM_STATUS_CODE}" == "401" ]]; then
		cat /tmp/team_ai_litellm_health.out | cat
	else
		echo "[ERROR] LiteLLM health check failed with status ${LITELLM_STATUS_CODE}" >&2
		exit 1
	fi
fi

if [[ -n "${LITELLM_MASTER_KEY:-}" ]]; then
	echo ""
	echo "[INFO] Checking LiteLLM models with master key..."
	curl -sS "http://localhost:4000/v1/models" \
		-H "Authorization: Bearer ${LITELLM_MASTER_KEY}" | cat
else
	echo ""
	echo "[WARN] LITELLM_MASTER_KEY is not set; skip /v1/models verification."
fi

echo ""
echo "[INFO] Checking Open WebUI..."
curl -sS "${WEBUI_URL}" | cat || true

echo ""
echo "[INFO] Checking Qdrant..."
curl -sS "${QDRANT_URL}" | cat
echo "[INFO] Qdrant is a backend vector store, not a normal user entrypoint."

echo ""
echo "[INFO] Health checks completed."
