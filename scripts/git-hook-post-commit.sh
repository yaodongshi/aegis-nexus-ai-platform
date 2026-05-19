#!/bin/bash
# Git Hook Post-Commit Script
# Auto-ingest commits into RAG knowledge base
# 
# Installation:
#   1. Copy this script to: .git/hooks/post-commit
#   2. chmod +x .git/hooks/post-commit
#   3. Restart git daemon or re-clone repository

set -e

# Configuration
API_URL="${TEAM_AI_PLATFORM_URL:-http://localhost:8000}"
VIRTUAL_KEY="${TEAM_AI_PLATFORM_KEY:-}"
CONFIG_FILE="${HOME}/.team/config.json"
ASYNC_QUEUE_MAX=10

# Logging
LOG_FILE="${HOME}/.team/git-hooks.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Exit gracefully if disabled
if [ -f "${HOME}/.team/disable-git-hooks" ]; then
    exit 0
fi

# Try to get virtual key from config
if [ -z "$VIRTUAL_KEY" ] && [ -f "$CONFIG_FILE" ]; then
    VIRTUAL_KEY=$(jq -r '.virtual_key // empty' "$CONFIG_FILE" 2>/dev/null || echo "")
fi

# If still no key, exit silently (not yet configured)
if [ -z "$VIRTUAL_KEY" ]; then
    exit 0
fi

# Collect commit info
HASH=$(git rev-parse HEAD)
MSG=$(git log -1 --pretty=%B | head -1)
AUTHOR=$(git log -1 --pretty=%an)
AUTHOR_EMAIL=$(git log -1 --pretty=%ae)
TIMESTAMP=$(git log -1 --pretty=%aI)

# Get repo info
REPO_NAME=$(basename "$(git rev-parse --show-toplevel)")
REPO_URL=$(git config --get remote.origin.url || echo "local")

# Extract tags from commit message
TAGS=("code-change")
if [[ $MSG == *"fix"* ]] || [[ $MSG == *"Fix"* ]]; then
    TAGS+=("bug-fix")
fi
if [[ $MSG == *"perf"* ]] || [[ $MSG == *"performance"* ]]; then
    TAGS+=("performance")
fi
if [[ $MSG == *"doc"* ]] || [[ $MSG == *"docs"* ]]; then
    TAGS+=("documentation")
fi
if [[ $MSG == *"test"* ]]; then
    TAGS+=("test")
fi

# Prepare payload
TAGS_JSON=$(printf '%s\n' "${TAGS[@]}" | jq -R . | jq -s .)

PAYLOAD=$(cat <<EOF
{
  "source": "git:commit",
  "source_ref": "$HASH",
  "content": "$MSG",
  "title": "$(echo $REPO_NAME | tr '[:lower:]' '[:upper:]'): $MSG",
  "author": "$AUTHOR",
  "author_email": "$AUTHOR_EMAIL",
  "tags": $TAGS_JSON,
  "timestamp": "$TIMESTAMP",
  "repo": "$REPO_NAME",
  "repo_url": "$REPO_URL",
  "project_id": "$REPO_NAME"
}
EOF
)

# Send to RAG API in background (non-blocking)
{
    curl -s -X POST "$API_URL/api/v1/knowledge" \
        -H "Authorization: Bearer $VIRTUAL_KEY" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        -m 5 \
        > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log "✅ 提交已发送到 RAG (提交: $HASH)"
    else
        log "⚠️  提交发送失败 (提交: $HASH) - 将在下次重试"
    fi
} &

# Don't wait for background task
exit 0
