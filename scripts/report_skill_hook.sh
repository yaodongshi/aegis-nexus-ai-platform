#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   TEAM_AI_PLATFORM_HOOK_SECRET=xxx bash scripts/report_skill_hook.sh --commit <sha>

API_BASE="${TEAM_AI_REPORT_API_BASE:-http://localhost:8000}"
REPO_NAME="${TEAM_AI_SKILL_REPO_NAME:-$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")}"
REPO_ID="${TEAM_AI_SKILL_REPO_ID:-}"
COMMIT_SHA=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --commit) COMMIT_SHA="$2"; shift 2 ;;
    --repo-name) REPO_NAME="$2"; shift 2 ;;
    --repo-id) REPO_ID="$2"; shift 2 ;;
    *)
      echo "[ERROR] Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${COMMIT_SHA}" ]]; then
  COMMIT_SHA="$(git rev-parse HEAD)"
fi

BRANCH="$(git branch --show-current 2>/dev/null || echo main)"

mapfile -t changed_files < <(git diff-tree --no-commit-id --name-only -r "$COMMIT_SHA" | grep -E '(^\.claude/skills/|^\.opencode/skills/|\.skill\.json$)' || true)

changed_json=$(printf '%s\n' "${changed_files[@]}" | sed '/^$/d' | sed 's/"/\\"/g' | awk 'BEGIN{printf "["} NF{if(c++) printf ","; printf "\"%s\"",$0} END{printf "]"}')
if [[ -z "${changed_json}" ]]; then
  changed_json="[]"
fi

payload=$(cat <<JSON
{
  "repository": "${REPO_NAME}",
  "repo_id": "${REPO_ID}",
  "branch": "${BRANCH}",
  "commit_sha": "${COMMIT_SHA}",
  "changed_files": ${changed_json}
}
JSON
)

headers=( -H "Content-Type: application/json" )

if [[ -n "${TEAM_AI_PLATFORM_HOOK_SECRET:-}" ]]; then
  sig=$(printf '%s' "$payload" | openssl dgst -sha256 -hmac "$TEAM_AI_PLATFORM_HOOK_SECRET" | sed 's/^.* //')
  headers+=( -H "X-Hook-Signature: sha256=${sig}" )
fi

idempotency_key=$(printf '%s|%s|%s' "${REPO_NAME}" "${BRANCH}" "${COMMIT_SHA}" | openssl dgst -sha256 | sed 's/^.* //')
headers+=( -H "X-Idempotency-Key: ${idempotency_key}" )

echo "[INFO] Reporting hook event: ${COMMIT_SHA} (${#changed_files[@]} files)"
curl -sS -X POST "${API_BASE}/api/skill-sync/hooks/report" "${headers[@]}" -d "${payload}" | cat
