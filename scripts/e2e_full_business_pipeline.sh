#!/usr/bin/env bash
# ╔════════════════════════════════════════════════════════════════════════════╗
# ║   Aegis Nexus AI Platform — Full Business Pipeline E2E                    ║
# ║   CLI → Git Repo → Hook(HMAC) → RAG → Skill → Agent → MCP Bundle          ║
# ║                                                                            ║
# ║   Required env:                                                            ║
# ║     API_BASE        (http://localhost:3000)                               ║
# ║     ADMIN_TOKEN     (sk-admin-local-change-me)                            ║
# ║     GIT_REMOTE_URL  (http://gitea.zodioo.com/diaojiaolou/testskill.git)   ║
# ║     GIT_USER GIT_PASSWORD                                                  ║
# ║                                                                            ║
# ║   testskill is cloned into backend/.aegis_e2e_repo/testskill so the       ║
# ║   container can see it via the ./backend bind-mount.                      ║
# ╚════════════════════════════════════════════════════════════════════════════╝

set -uo pipefail

API_BASE="${API_BASE:-http://localhost:3000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-sk-admin-local-change-me}"
GIT_REMOTE_URL="${GIT_REMOTE_URL:-http://gitea.zodioo.com/diaojiaolou/testskill.git}"
GIT_USER="${GIT_USER:-diaojiaolou}"
GIT_PASSWORD="${GIT_PASSWORD:-yds870928}"

PLATFORM_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST_REPO_DIR="$PLATFORM_ROOT/backend/.aegis_e2e_repo/testskill"
CONTAINER_REPO_DIR="/app/backend/.aegis_e2e_repo/testskill"
VECTOR_SCRIPT="$PLATFORM_ROOT/scripts/vector_store_management.sh"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
PASS=0; FAIL=0
declare -a FAIL_LOG=()

ok()    { echo -e "${GREEN}[OK]${NC} $*"; PASS=$((PASS+1)); }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; FAIL=$((FAIL+1)); FAIL_LOG+=("$*"); }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log()   { echo -e "${BLUE}[*]${NC} $*"; }
header(){ echo; echo -e "${BLUE}════════ $1 ════════${NC}"; }

load_env_var_from_file() {
  local key="$1"
  local env_file="$2"
  if [[ ! -f "$env_file" ]]; then
    return 1
  fi
  python3 - "$key" "$env_file" <<'PY'
import sys
key = sys.argv[1]
path = sys.argv[2]
value = ""
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        if k.strip() == key:
            value = v.strip().strip('"').strip("'")
            break
print(value)
PY
}

curl_admin() {
  local method="$1"; local path="$2"; local body="${3:-}"
  if [[ -n "$body" ]]; then
    curl -sS -X "$method" "$API_BASE$path" -H "X-Admin-Token: $ADMIN_TOKEN" \
      -H 'Content-Type: application/json' -d "$body" -m 30
  else
    curl -sS -X "$method" "$API_BASE$path" -H "X-Admin-Token: $ADMIN_TOKEN" -m 30
  fi
}

# ─── Stage 0: Pre-flight ─────────────────────────────────────────────────────
header "Stage 0: Pre-flight"
HEALTH=$(curl_admin GET /api/platform/runtime-health || true)
if echo "$HEALTH" | grep -q '"ok":true'; then
  MC=$(echo "$HEALTH" | python3 -c "import sys,json;print(json.load(sys.stdin).get('model_count',0))")
  ok "Backend healthy, gateway models=$MC"
else
  fail "Backend health failed: $HEALTH"; exit 1
fi

# ─── Stage 1: CLI clone testskill ────────────────────────────────────────────
header "Stage 1: CLI — clone testskill into backend-mounted path"
mkdir -p "$(dirname "$HOST_REPO_DIR")"
CLONE_URL="http://${GIT_USER}:${GIT_PASSWORD}@$(echo "$GIT_REMOTE_URL" | sed 's|http://||')"
if [[ ! -d "$HOST_REPO_DIR/.git" ]]; then
  rm -rf "$HOST_REPO_DIR"
  if git clone "$CLONE_URL" "$HOST_REPO_DIR" 2>&1 | tail -3; then
    ok "Cloned $GIT_REMOTE_URL"
  else
    fail "Failed to clone"; exit 1
  fi
else
  ok "Repo already at $HOST_REPO_DIR"
fi
cd "$HOST_REPO_DIR"
git config user.email "e2e@aegis.local" >/dev/null
git config user.name  "Aegis E2E"        >/dev/null
git remote set-url origin "$CLONE_URL" 2>/dev/null || true

mkdir -p .claude/skills
TS_TAG="$(date +%s)"
SKILL_FILE=".claude/skills/refactor-helper.skill.json"
cat > "$SKILL_FILE" <<JSON
{
  "name": "refactor-helper-$TS_TAG",
  "description": "Helps refactor legacy Python services into clean async pipelines.",
  "system_prompt": "You are a senior Python refactoring assistant. Always preserve behavior, add type hints, and propose tests.",
  "category": "engineering",
  "tags": ["python","refactor","async"],
  "version": "v1",
  "metadata": {"origin":"aegis-e2e-pipeline","generated_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
}
JSON
git add "$SKILL_FILE"
if ! git diff --cached --quiet; then
  git commit -m "feat(skill): refactor-helper-$TS_TAG via e2e" >/dev/null
  ok "Committed skill manifest"
else
  ok "Skill manifest already committed"
fi
if git push -u origin HEAD:main >/dev/null 2>&1; then
  ok "Pushed to remote main"
else
  warn "Push no-op or rejected"
fi
COMMIT_SHA=$(git rev-parse HEAD)
log "HEAD: $COMMIT_SHA"

# ─── Stage 2: Register git repo ──────────────────────────────────────────────
header "Stage 2: Register git repo (container path)"
GIT_REPO_BODY=$(python3 -c "
import json
print(json.dumps({'name':'testskill-e2e-$TS_TAG','path':'$CONTAINER_REPO_DIR',
'branch':'main','auto_commit':False,'make_active':True}))")
# Reuse existing repo by container path if already registered (idempotent)
EXISTING=$(curl_admin GET "/api/git-repos?limit=200")
REPO_ID=$(EX="$EXISTING" CP="$CONTAINER_REPO_DIR" python3 -c "
import os,json
d=json.loads(os.environ['EX'])
items=d.get('items',[]) if isinstance(d,dict) else d
for it in items:
    if it.get('path')==os.environ['CP']:
        print(it.get('id','')); break")
if [[ -n "$REPO_ID" ]]; then
  ok "Reusing existing git repo: $REPO_ID"
else
  GIT_RESP=$(curl_admin POST /api/git-repos "$GIT_REPO_BODY")
  REPO_ID=$(echo "$GIT_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
  if [[ -n "$REPO_ID" ]]; then ok "Created git repo: $REPO_ID"; else fail "Create failed: $GIT_RESP"; exit 1; fi
fi
# Make sure it's active
curl_admin POST "/api/git-repos/$REPO_ID/activate" >/dev/null || true

PROBE_RESP=$(curl_admin GET "/api/git-repos/$REPO_ID/probe")
if echo "$PROBE_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin);sys.exit(0 if d.get('is_git_repo') and d.get('git_available') else 1)"; then
  ok "Probe succeeded inside container"
else
  fail "Probe failed: $PROBE_RESP"
fi

PULL_RESP=$(curl_admin POST "/api/git-repos/$REPO_ID/pull" '{}')
PULLED=$(echo "$PULL_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('pulled',False))" 2>/dev/null)
SCAN=$(echo "$PULL_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('scanned_files',0))" 2>/dev/null)
ok "Git pull: pulled=$PULLED scanned_files=$SCAN"

# ─── Stage 3: Hook secret rotate + signed report ─────────────────────────────
header "Stage 3: Rotate hook secret & report HMAC-signed event"
NEW_SECRET="aegis-e2e-$TS_TAG"
ROTATE=$(curl_admin POST /api/skill-sync/hooks/secret/rotate "{\"new_secret\":\"$NEW_SECRET\"}")
SECRET=$(echo "$ROTATE" | python3 -c "import sys,json;print(json.load(sys.stdin).get('new_secret',''))" 2>/dev/null || echo "")
if [[ -n "$SECRET" ]]; then ok "Rotated hook secret (db source)"; else fail "Rotate failed: $ROTATE"; fi

HOOK_PAYLOAD=$(python3 -c "
import json
print(json.dumps({'repository':'testskill-e2e-$TS_TAG','repo_id':'$REPO_ID',
'branch':'main','commit_sha':'$COMMIT_SHA','changed_files':['$SKILL_FILE'],
'event_id':'e2e-$TS_TAG','author':'aegis-e2e'},separators=(',',':')))")
HOOK_SIG=$(SECRET="$SECRET" PAYLOAD="$HOOK_PAYLOAD" python3 -c "
import os,hmac,hashlib
print('sha256='+hmac.new(os.environ['SECRET'].encode(),os.environ['PAYLOAD'].encode(),hashlib.sha256).hexdigest())")

HOOK_RESP=$(curl -sS -X POST "$API_BASE/api/skill-sync/hooks/report" \
  -H "X-Hook-Signature: $HOOK_SIG" -H 'Content-Type: application/json' \
  --data-raw "$HOOK_PAYLOAD" -m 30)
HOOK_EID=$(echo "$HOOK_RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(d.get('hook_event_id') or d.get('event_id') or (d.get('event') or {}).get('id') or d.get('id') or '')" 2>/dev/null || echo "")
if [[ -n "$HOOK_EID" ]]; then ok "Signed hook accepted: $HOOK_EID"; else fail "Signed hook rejected: $HOOK_RESP"; fi

EVL=$(curl_admin GET /api/skill-sync/hooks/events)
EC=$(echo "$EVL" | python3 -c "import sys,json;d=json.load(sys.stdin);i=d if isinstance(d,list) else d.get('items',[]);print(len(i))" 2>/dev/null || echo "0")
if [[ "$EC" -ge 1 ]]; then ok "Hook events listed (count=$EC)"; else fail "Hook events list empty"; fi

# ─── Stage 4: RAG ingest ─────────────────────────────────────────────────────
header "Stage 4: RAG ingest → Qdrant"
RAG_BODY=$(python3 -c "
import json
print(json.dumps({'items':[
{'source_type':'session','source_id':'e2e-rag-$TS_TAG-1','title':'Async batching',
 'content':'Refactor sync I/O to asyncio.gather; never block with time.sleep — use asyncio.sleep. Add type hints and tests.',
 'tags':['python','refactor','async'],'quality_score':0.85,'metadata':{'origin':'aegis-e2e'}},
{'source_type':'cli','source_id':'e2e-rag-$TS_TAG-2','title':'Connection pooling',
 'content':'Introduce shared asyncpg/httpx pool when migrating sync→async; else fd table exhausts.',
 'tags':['python','pool','production'],'quality_score':0.8,'metadata':{'origin':'aegis-e2e'}}],
'min_quality_score':0.6,'created_by':'aegis-e2e-cli'}))")
RAG_RESP=$(curl_admin POST /api/evolution/gateway-knowledge/ingest "$RAG_BODY")
ACC=$(echo "$RAG_RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('accepted',0))" 2>/dev/null || echo 0)
if [[ "$ACC" -ge 1 ]]; then ok "Ingested $ACC RAG items"; else fail "RAG accepted=$ACC: $RAG_RESP"; fi

# ─── Stage 5: Task-run report → apply ─────────────────────────────────────────
header "Stage 5: Task-run report → skill update → apply"
TASK_BODY=$(python3 -c "
import json
print(json.dumps({'tool_type':'codex','user_id':'aegis-e2e',
'task_title':'Refactor sync HTTP client to async',
'summary':'Migrated requests→httpx.AsyncClient with shared pool; tests green.',
'lessons_learned':'Wrap pool init in app lifespan; never spawn per-request.',
'proposed_skill_name':'async-httpx-refactor-$TS_TAG',
'proposed_system_prompt':'You guide engineers through async refactors.',
'proposed_user_prompt_template':'Refactor:\n{{code}}'}))")
TASK_RESP=$(curl_admin POST /api/task-runs/report "$TASK_BODY")
SU_ID=$(echo "$TASK_RESP" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('skill_update',{}).get('id',''))" 2>/dev/null || echo "")
if [[ -n "$SU_ID" ]]; then ok "Task-run reported, update=$SU_ID"; else fail "Task-run: $TASK_RESP"; fi

if [[ -n "$SU_ID" ]]; then
  APP=$(curl_admin POST "/api/skill-updates/$SU_ID/apply" '{}')
  SKILL_ID=$(echo "$APP" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('skill_id') or d.get('id') or '')" 2>/dev/null || echo "")
  if [[ -n "$SKILL_ID" ]]; then ok "Skill update applied → $SKILL_ID"; else fail "Apply: $APP"; fi
fi

# ─── Stage 6: Skill CRUD + search ────────────────────────────────────────────
header "Stage 6: Skill CRUD & semantic search (query=…)"
CREATE_BODY=$(python3 -c "
import json
print(json.dumps({'name':'e2e-direct-skill-$TS_TAG',
'description':'Direct skill for e2e validation.',
'system_prompt':'Always respond in JSON when invoked.',
'category':'engineering','tags':['e2e','json-mode']}))")
SR=$(curl_admin POST /api/skills "$CREATE_BODY")
DSI=$(echo "$SR" | python3 -c "import sys,json;print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
if [[ -n "$DSI" ]]; then ok "Created skill: $DSI"; else fail "Skill create: $SR"; fi

SEARCH=$(curl_admin GET "/api/skills/search?query=refactor&limit=5")
SC=$(echo "$SEARCH" | python3 -c "import sys,json;d=json.load(sys.stdin);i=d if isinstance(d,list) else d.get('items',[]);print(len(i))" 2>/dev/null || echo "0")
if [[ "$SC" -ge 1 ]]; then ok "Skill search 'refactor' → $SC hits"; else fail "Search 0 hits: $(echo "$SEARCH"|head -c 200)"; fi

SS=$(curl_admin GET /api/skills/search-status)
MODE=$(echo "$SS" | python3 -c "import sys,json;print(json.load(sys.stdin).get('mode','?'))" 2>/dev/null || echo "?")
ok "Search mode: $MODE"

# ─── Stage 7: RAG→Skill summarize ────────────────────────────────────────────
header "Stage 7: RAG → Skill summarization"
SUM=$(curl_admin POST /api/evolution/rag-to-skill/summarize '{"scope":"team","limit":20,"created_by":"aegis-e2e"}')
SCAN_N=$(echo "$SUM" | python3 -c "import sys,json;print(json.load(sys.stdin).get('scanned',0))" 2>/dev/null || echo 0)
GEN_N=$(echo "$SUM" | python3 -c "import sys,json;print(json.load(sys.stdin).get('generated_updates',0))" 2>/dev/null || echo 0)
ok "Summarize: scanned=$SCAN_N generated=$GEN_N"

# ─── Stage 8: RAG→Agent workflow ─────────────────────────────────────────────
header "Stage 8: RAG → Agent workflow generation"
AG=$(curl_admin POST /api/evolution/rag-to-agent/generate '{"scope":"team","limit":10,"created_by":"aegis-e2e"}')
WID=$(echo "$AG" | python3 -c "
import sys,json
try:
  d=json.load(sys.stdin)
  print(d.get('workflow_id') or (d.get('workflow') or {}).get('workflow_id') or (d.get('workflow') or {}).get('id') or '')
except Exception: print('')" 2>/dev/null || echo "")
if [[ -n "$WID" ]]; then ok "Generated workflow: $WID"; else fail "Workflow gen: $(echo "$AG"|head -c 250)"; fi

WL=$(curl_admin GET /api/evolution/rag-to-agent/workflows)
WC=$(echo "$WL" | python3 -c "import sys,json;d=json.load(sys.stdin);i=d if isinstance(d,list) else d.get('items',[]);print(len(i))" 2>/dev/null || echo "0")
ok "Workflows total: $WC"

# ─── Stage 9: MCP bundle / team-rules ────────────────────────────────────────
header "Stage 9: MCP — bundle + team-rules"
BSI="${SKILL_ID:-$DSI}"
TEAM_ID="team-e2e-$TS_TAG"
BB=$(python3 -c "
import json
print(json.dumps({'team_id':'$TEAM_ID','skill_id':'$BSI','version':'v1',
'bundle':{'manifest':{'name':'refactor-helper','version':'v1'},
'prompts':['system: be precise','user: refactor this']},
'tags':['e2e','mcp'],'uploaded_by':'aegis-e2e'}))")
BR=$(curl_admin POST /api/skill-sync/mcp/skill-bundles/upload "$BB")
BID=$(echo "$BR" | python3 -c "import sys,json;d=json.load(sys.stdin);print((d.get('bundle') or {}).get('bundle_id',''))" 2>/dev/null || echo "")
if [[ -n "$BID" ]]; then ok "Bundle uploaded: $BID"; else fail "Bundle upload: $BR"; fi

# team_id as query param
RR=$(curl_admin POST "/api/skill-sync/mcp/team-rules/generate?team_id=$TEAM_ID" '{}')
RSID=$(echo "$RR" | python3 -c "import sys,json;d=json.load(sys.stdin);print((d.get('rule') or {}).get('rule_set_id',''))" 2>/dev/null || echo "")
if [[ -n "$RSID" ]]; then
  ok "Team rules: $RSID"
  AR=$(curl_admin POST "/api/skill-sync/mcp/team-rules/$RSID/apply?team_id=$TEAM_ID" '{"dry_run":true}')
  if echo "$AR" | python3 -c "import sys,json;sys.exit(0 if json.load(sys.stdin).get('dry_run') else 1)"; then
    ok "Team-rules apply (dry-run) ok"
  else
    fail "Apply: $AR"
  fi
else
  fail "Rules gen: $RR"
fi

DL=$(curl_admin GET "/api/skill-sync/mcp/skill-bundles/download?bundle_id=$BID")
if echo "$DL" | grep -qE '"manifest"|"prompts"|"skill_id"|"bundle"'; then
  ok "Bundle download payload ok"
else
  fail "Download: $(echo "$DL"|head -c 200)"
fi

# ─── Stage 10: Skill pack export ─────────────────────────────────────────────
header "Stage 10: Skill pack export (claude / opencode)"
if [[ -n "$BSI" ]]; then
  for T in claude-code opencode; do
    P=$(curl_admin GET "/api/skills/$BSI/pack/$T")
    if echo "$P" | grep -qE '"files"|"manifest"|"skill"|"target"'; then
      ok "Pack target=$T ok"
    else
      warn "Pack target=$T: $(echo "$P"|head -c 150)"
    fi
  done
fi

# ─── Stage 11: Evolution overview ────────────────────────────────────────────
header "Stage 11: Evolution overview & action ledger"
OVR=$(curl_admin GET /api/evolution/overview)
B=$(echo "$OVR" | python3 -c "import sys,json;print(json.load(sys.stdin).get('skill_bundle_total',0))" 2>/dev/null || echo 0)
R=$(echo "$OVR" | python3 -c "import sys,json;print(json.load(sys.stdin).get('team_rule_total',0))" 2>/dev/null || echo 0)
ok "Overview: bundles=$B rules=$R"

AC=$(curl_admin GET /api/evolution/actions)
ACT=$(echo "$AC" | python3 -c "import sys,json;d=json.load(sys.stdin);i=d if isinstance(d,list) else d.get('items',[]);print(len(i))" 2>/dev/null || echo 0)
ok "Action logs: $ACT"

# ─── Stage 12: Vector Store create/manage/test ──────────────────────────────
header "Stage 12: Vector Store Management smoke"
if [[ -z "${LITELLM_MASTER_KEY:-}" ]]; then
  LITELLM_MASTER_KEY="$(load_env_var_from_file LITELLM_MASTER_KEY "$PLATFORM_ROOT/.env" || true)"
fi

if [[ ! -x "$VECTOR_SCRIPT" ]]; then
  fail "Vector script missing or not executable: $VECTOR_SCRIPT"
elif [[ -z "${LITELLM_MASTER_KEY:-}" ]]; then
  fail "LITELLM_MASTER_KEY is required for vector smoke test"
else
  export LITELLM_MASTER_KEY
  export QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
  export LITELLM_BASE_URL="${LITELLM_BASE_URL:-http://localhost:4000}"
  export EMBEDDING_MODEL="${EMBEDDING_MODEL:-text-embedding-v3}"
  export VECTOR_SIZE="${VECTOR_SIZE:-1024}"

  VS_COLLECTION="e2e_vector_${TS_TAG}"

  CREATE_OUT=$(bash "$VECTOR_SCRIPT" create "$VS_COLLECTION" "$VECTOR_SIZE" Cosine 2>&1 || true)
  if echo "$CREATE_OUT" | grep -qi '"status"\s*:\s*"ok"'; then
    ok "Vector store created: $VS_COLLECTION"
  else
    fail "Vector create failed: $(echo "$CREATE_OUT" | tail -n 2)"
  fi

  UPSERT_OUT=$(bash "$VECTOR_SCRIPT" upsert-text "$VS_COLLECTION" "doc_${TS_TAG}" "refactor sync I/O to async with pooling" '{"source":"e2e","tag":"vector"}' 2>&1 || true)
  if echo "$UPSERT_OUT" | grep -qi '"status"\s*:\s*"ok"'; then
    ok "Vector upsert succeeded"
  else
    fail "Vector upsert failed: $(echo "$UPSERT_OUT" | tail -n 2)"
  fi

  SEARCH_OUT=$(bash "$VECTOR_SCRIPT" search "$VS_COLLECTION" "async pooling refactor" 3 2>&1 || true)
  SEARCH_HITS=$(echo "$SEARCH_OUT" | python3 -c "import sys,json,re
t=sys.stdin.read()
m=re.search(r'\{.*\}', t, re.S)
if not m:
    print(0); raise SystemExit
d=json.loads(m.group(0))
r=d.get('result',[])
print(len(r) if isinstance(r,list) else 0)")
  if [[ "${SEARCH_HITS:-0}" -ge 1 ]]; then
    ok "Vector search returned hits=$SEARCH_HITS"
  else
    fail "Vector search returned 0 hits"
  fi

  STATS_OUT=$(bash "$VECTOR_SCRIPT" stats "$VS_COLLECTION" 2>&1 || true)
  if echo "$STATS_OUT" | grep -qi '"status"\s*:\s*"ok"'; then
    ok "Vector stats query ok"
  else
    fail "Vector stats failed: $(echo "$STATS_OUT" | tail -n 2)"
  fi
fi

# ─── Summary ─────────────────────────────────────────────────────────────────
header "Summary"
echo
echo "Passed:  $PASS"
echo "Failed:  $FAIL"
if [[ $FAIL -gt 0 ]]; then
  echo; echo "Failures:"
  for f in "${FAIL_LOG[@]}"; do echo "  - $f"; done
  exit 1
fi
echo -e "${GREEN}All e2e business pipeline stages passed.${NC}"
exit 0
