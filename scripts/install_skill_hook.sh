#!/usr/bin/env bash
set -euo pipefail

# Install post-commit hook for Claude/OpenCode skill sync events.
# Usage:
#   bash scripts/install_skill_hook.sh --repo /path/to/repo --api-base http://localhost:8000

REPO_PATH="$(pwd)"
API_BASE="${TEAM_AI_REPORT_API_BASE:-http://localhost:8000}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_PATH="$2"; shift 2 ;;
    --api-base) API_BASE="$2"; shift 2 ;;
    *)
      echo "[ERROR] Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

REPO_PATH="$(cd "$REPO_PATH" && pwd)"
if [[ ! -d "$REPO_PATH/.git" ]]; then
  echo "[ERROR] Not a git repository: $REPO_PATH" >&2
  exit 1
fi

HOOK_PATH="$REPO_PATH/.git/hooks/post-commit"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cat > "$HOOK_PATH" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export TEAM_AI_REPORT_API_BASE="${API_BASE}"
"${SCRIPT_DIR}/report_skill_hook.sh" --commit "\$(git rev-parse HEAD)"
EOF

chmod +x "$HOOK_PATH"
echo "[OK] Installed post-commit hook at $HOOK_PATH"
echo "[TIP] Configure TEAM_AI_PLATFORM_HOOK_SECRET in your environment for signed events."
