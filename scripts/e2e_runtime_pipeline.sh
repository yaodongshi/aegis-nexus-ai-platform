#!/usr/bin/env bash
set -euo pipefail

# Solution A E2E pipeline check:
# 1) Control-plane runtime config preview/apply
# 2) LiteLLM health + models check
# 3) Optional chat probe with fresh virtual key

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPORT_DIR="${PROJECT_ROOT}/reports"

BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://localhost:8000}"
GATEWAY_BASE_URL="${GATEWAY_BASE_URL:-http://localhost:4000}"
ADMIN_TOKEN="${TEAM_AI_PLATFORM_ADMIN_TOKEN:-}"
MASTER_KEY="${LITELLM_MASTER_KEY:-}"

mkdir -p "${REPORT_DIR}"
REPORT_FILE="${REPORT_DIR}/e2e_runtime_pipeline_$(date +%Y%m%d_%H%M%S).log"

log() {
  local level="$1"
  local msg="$2"
  printf '[%s] %s\n' "${level}" "${msg}" | tee -a "${REPORT_FILE}"
}

curl_with_optional_admin() {
  local method="$1"
  local url="$2"
  local body="${3:-}"

  local args=("-sS" "-X" "${method}" "${url}")
  if [[ -n "${ADMIN_TOKEN}" ]]; then
    args+=("-H" "X-Admin-Token: ${ADMIN_TOKEN}")
  fi
  if [[ -n "${body}" ]]; then
    args+=("-H" "Content-Type: application/json" "-d" "${body}")
  fi

  curl "${args[@]}"
}

log INFO "Report file: ${REPORT_FILE}"
log INFO "Step 1/6: Check backend health"
if curl -fsS "${BACKEND_BASE_URL}/health" >/dev/null; then
  log PASS "Backend health check passed"
else
  log FAIL "Backend health check failed"
  exit 1
fi

log INFO "Step 2/6: Preview runtime config"
PREVIEW_JSON="$(curl_with_optional_admin GET "${BACKEND_BASE_URL}/api/v1/runtime/litellm-config")"
PROVIDER_COUNT="$(echo "${PREVIEW_JSON}" | jq -r '.provider_count // 0')"
MODEL_COUNT="$(echo "${PREVIEW_JSON}" | jq -r '.model_count // 0')"
OBS_BACKEND="$(echo "${PREVIEW_JSON}" | jq -r '.observability_backend // "none"')"
log PASS "Runtime preview: providers=${PROVIDER_COUNT}, models=${MODEL_COUNT}, observability=${OBS_BACKEND}"

log INFO "Step 3/6: Apply runtime config and restart gateway"
(
  cd "${PROJECT_ROOT}"
  TEAM_AI_PLATFORM_ADMIN_TOKEN="${ADMIN_TOKEN}" BACKEND_BASE_URL="${BACKEND_BASE_URL}" bash scripts/apply_litellm_gateway.sh
) | tee -a "${REPORT_FILE}"
log PASS "Runtime apply script finished"

log INFO "Step 4/6: Check LiteLLM health"
if curl -fsS "${GATEWAY_BASE_URL}/health" >/dev/null; then
  log PASS "LiteLLM health check passed"
else
  log FAIL "LiteLLM health check failed"
  exit 1
fi

if [[ -n "${MASTER_KEY}" ]]; then
  log INFO "Step 5/6: Check gateway models with master key"
  MODELS_JSON="$(curl -sS "${GATEWAY_BASE_URL}/v1/models" -H "Authorization: Bearer ${MASTER_KEY}")"
  GATEWAY_MODEL_COUNT="$(echo "${MODELS_JSON}" | jq -r '.data | length')"
  log PASS "Gateway models count=${GATEWAY_MODEL_COUNT}"

  if [[ "${GATEWAY_MODEL_COUNT}" -gt 0 ]]; then
    TARGET_MODEL="$(echo "${MODELS_JSON}" | jq -r '.data[0].id')"
    KEY_ALIAS="e2e-runtime-$(date +%s)"

    log INFO "Step 6/6: Generate virtual key and run chat probe"
    KEY_JSON="$(curl -sS "${GATEWAY_BASE_URL}/key/generate" \
      -H "Authorization: Bearer ${MASTER_KEY}" \
      -H "Content-Type: application/json" \
      -d "{\"models\":[\"${TARGET_MODEL}\"],\"duration\":\"1d\",\"key_alias\":\"${KEY_ALIAS}\"}")"
    KEY_VALUE="$(echo "${KEY_JSON}" | jq -r '.key // empty')"

    if [[ -z "${KEY_VALUE}" ]]; then
      log FAIL "Failed to generate virtual key"
      exit 1
    fi

    CHAT_JSON="$(curl -sS "${GATEWAY_BASE_URL}/v1/chat/completions" \
      -H "Authorization: Bearer ${KEY_VALUE}" \
      -H "Content-Type: application/json" \
      -d "{\"model\":\"${TARGET_MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"reply OK only\"}]}")"
    CHAT_TEXT="$(echo "${CHAT_JSON}" | jq -r '.choices[0].message.content // .error.message // ""')"

    if [[ -n "${CHAT_TEXT}" ]]; then
      log PASS "Chat probe succeeded: ${CHAT_TEXT}"
    else
      log FAIL "Chat probe returned empty response"
      exit 1
    fi
  else
    log WARN "No models in gateway, skip chat probe"
  fi
else
  log WARN "LITELLM_MASTER_KEY not set, skip model and chat probes"
fi

log PASS "Solution A runtime pipeline E2E completed"
