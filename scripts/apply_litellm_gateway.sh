#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODE="${1:-apply}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://localhost:8000}"
ADMIN_TOKEN="${TEAM_AI_PLATFORM_ADMIN_TOKEN:-}"

if [[ "${MODE}" != "apply" && "${MODE}" != "check" ]]; then
  echo "[ERROR] Unsupported mode: ${MODE}" >&2
  echo "[INFO] Usage: bash scripts/apply_litellm_gateway.sh [apply|check]" >&2
  exit 1
fi

cd "${PROJECT_ROOT}"

if [[ ! -f ".env" ]]; then
  echo "[ERROR] Missing .env in ${PROJECT_ROOT}" >&2
  echo "[INFO] Copy .env.example to .env before running this script." >&2
  exit 1
fi

if [[ "${MODE}" == "check" ]]; then
  echo "[INFO] Check mode: printing current LiteLLM models endpoint status"
  if [[ -n "${LITELLM_MASTER_KEY:-}" ]]; then
    curl -sS "http://localhost:4000/v1/models" \
      -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" | cat
  else
    echo "[WARN] LITELLM_MASTER_KEY is not set; skip /v1/models check."
    echo "[INFO] Export key then rerun:"
    echo "       export LITELLM_MASTER_KEY=sk-team-master-change-me"
    echo "       bash scripts/apply_litellm_gateway.sh check"
  fi
  exit 0
fi

echo "[INFO] Applying runtime config from control plane..."
AUTH_HEADER=()
if [[ -n "${ADMIN_TOKEN}" ]]; then
  AUTH_HEADER=(-H "X-Admin-Token: ${ADMIN_TOKEN}")
fi

if ! curl -fsS -X POST "${BACKEND_BASE_URL}/api/v1/runtime/litellm-config/apply" \
  -H "Content-Type: application/json" \
  "${AUTH_HEADER[@]}" \
  -d '{}' >/tmp/team_ai_runtime_apply.json 2>/tmp/team_ai_runtime_apply.err; then
  echo "[ERROR] Failed to apply runtime config via control plane API." >&2
  echo "[ERROR] Endpoint: ${BACKEND_BASE_URL}/api/v1/runtime/litellm-config/apply" >&2
  if [[ -s /tmp/team_ai_runtime_apply.err ]]; then
    cat /tmp/team_ai_runtime_apply.err >&2
  fi
  exit 1
fi

echo "[INFO] Runtime config apply response:"
cat /tmp/team_ai_runtime_apply.json | cat

echo "[INFO] Restarting LiteLLM gateway to apply latest config files..."
docker compose restart litellm

echo "[INFO] Waiting for LiteLLM health endpoint..."
for _ in {1..30}; do
  if curl -fsS "http://localhost:4000/health" >/dev/null 2>&1; then
    echo "[INFO] LiteLLM health is ready."
    break
  fi
  sleep 1
done

if ! curl -fsS "http://localhost:4000/health" >/dev/null 2>&1; then
  echo "[ERROR] LiteLLM health endpoint is not ready after restart." >&2
  exit 1
fi

echo "[INFO] Gateway config apply completed."
echo "[INFO] Optional model list verification:"
echo "       export LITELLM_MASTER_KEY=sk-team-master-change-me"
echo "       bash scripts/apply_litellm_gateway.sh check"
