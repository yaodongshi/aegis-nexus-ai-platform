#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"

REQUESTS='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"health.ping","arguments":{}}}'

OUT=$(printf "%s\n" "$REQUESTS" | python -m mcp_server.main)

OUT_JSON="$OUT" python - <<'PY'
import json
import os

lines = [line.strip() for line in os.environ.get("OUT_JSON", "").splitlines() if line.strip()]
if len(lines) != 3:
	raise SystemExit(1)

resp1 = json.loads(lines[0])
resp2 = json.loads(lines[1])
resp3 = json.loads(lines[2])

if resp1.get("id") != 1:
	raise SystemExit(1)
if resp2.get("id") != 2:
	raise SystemExit(1)
tools = resp2.get("result", {}).get("tools", [])
if not any(item.get("name") == "health.ping" for item in tools if isinstance(item, dict)):
	raise SystemExit(1)
if resp3.get("id") != 3:
	raise SystemExit(1)

content = resp3.get("result", {}).get("content", [])
if not content:
	raise SystemExit(1)
text_payload = content[0].get("text", "")
parsed_payload = json.loads(text_payload)
if parsed_payload.get("ok") is not True:
	raise SystemExit(1)
PY

echo "MCP server smoke test passed"
