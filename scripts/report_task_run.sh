#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   TEAM_AI_PLATFORM_AGENT_TOKEN=xxx bash scripts/report_task_run.sh \
#     --tool codex --user u_zhangsan --title "修复任务" \
#     --summary "完成修复" --lessons "先写最小回归测试"

API_BASE="${TEAM_AI_REPORT_API_BASE:-http://localhost:8000}"
TOOL_TYPE="codex"
USER_ID="unknown"
TITLE=""
SUMMARY=""
ERROR_LOG=""
LESSONS=""
SKILL_NAME=""
SYSTEM_PROMPT=""
USER_PROMPT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool) TOOL_TYPE="$2"; shift 2 ;;
    --user) USER_ID="$2"; shift 2 ;;
    --title) TITLE="$2"; shift 2 ;;
    --summary) SUMMARY="$2"; shift 2 ;;
    --error) ERROR_LOG="$2"; shift 2 ;;
    --lessons) LESSONS="$2"; shift 2 ;;
    --skill-name) SKILL_NAME="$2"; shift 2 ;;
    --system-prompt) SYSTEM_PROMPT="$2"; shift 2 ;;
    --user-prompt) USER_PROMPT="$2"; shift 2 ;;
    *)
      echo "[ERROR] Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${TITLE}" || -z "${SUMMARY}" ]]; then
  echo "[ERROR] --title and --summary are required" >&2
  exit 1
fi

headers=( -H "Content-Type: application/json" )
if [[ -n "${TEAM_AI_PLATFORM_AGENT_TOKEN:-}" ]]; then
  headers+=( -H "X-Agent-Token: ${TEAM_AI_PLATFORM_AGENT_TOKEN}" )
fi

payload=$(cat <<JSON
{
  "tool_type": "${TOOL_TYPE}",
  "user_id": "${USER_ID}",
  "task_title": "${TITLE}",
  "summary": "${SUMMARY}",
  "error_log": "${ERROR_LOG}",
  "lessons_learned": "${LESSONS}",
  "proposed_skill_name": "${SKILL_NAME}",
  "proposed_system_prompt": "${SYSTEM_PROMPT}",
  "proposed_user_prompt_template": "${USER_PROMPT}"
}
JSON
)

echo "[INFO] Reporting task run to ${API_BASE}/api/task-runs/report"
curl -sS -X POST "${API_BASE}/api/task-runs/report" "${headers[@]}" -d "${payload}" | cat
