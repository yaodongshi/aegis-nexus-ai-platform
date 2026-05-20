#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BACKEND_DIR="$ROOT_DIR/backend"
PORT=8123

cd "$BACKEND_DIR"

python -m uvicorn mcp_server.http_app:app --host 127.0.0.1 --port "$PORT" >/tmp/team_ai_mcp_http.log 2>&1 &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

python - <<'PY'
from __future__ import annotations
import time
import urllib.error
import urllib.request

url = "http://127.0.0.1:8123/health"
deadline = time.time() + 8
while time.time() < deadline:
        try:
                with urllib.request.urlopen(url, timeout=1) as response:
                        if response.status == 200:
                                break
        except urllib.error.URLError:
                time.sleep(0.2)
else:
        raise SystemExit(1)
PY

python - <<'PY'
from __future__ import annotations
import json
import urllib.request

base = "http://127.0.0.1:8123"
health = json.loads(urllib.request.urlopen(f"{base}/health", timeout=10).read().decode("utf-8"))
if health.get("ok") is not True:
    raise SystemExit(1)

req = urllib.request.Request(
    f"{base}/rpc",
    data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
items = resp.get("result", {}).get("tools", [])
names = {item.get("name") for item in items if isinstance(item, dict)}
required = {"skills.list", "skills.get_prompt", "rag.search", "task_runs.report", "health.ping"}
if not required.issubset(names):
    raise SystemExit(1)
PY

echo "MCP HTTP integration test passed"
