#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:4000}"
MASTER_KEY="${LITELLM_MASTER_KEY:-}"

if [[ -z "${MASTER_KEY}" ]]; then
  echo "[ERROR] LITELLM_MASTER_KEY env var is required." >&2
  echo "[INFO] Example: export LITELLM_MASTER_KEY=sk-team-master-change-me" >&2
  exit 1
fi

PAYLOAD='{
  "models": ["gpt-5", "gpt-4.1", "claude-sonnet-4", "gemini-2.5-pro"],
  "duration": "30d",
  "key_alias": "team-dev-default",
  "metadata": {
    "owner": "platform-team",
    "scope": "engineering"
  }
}'

echo "[INFO] Creating virtual key via ${BASE_URL}/key/generate"

curl -sS "${BASE_URL}/key/generate" \
  -H "Authorization: Bearer ${MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}" | cat

echo ""
echo "[INFO] Save returned key securely and distribute by user/project scope only."
