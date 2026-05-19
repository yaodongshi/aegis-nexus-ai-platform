#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${1:-http://localhost:3000/health}"
LITELLM_URL="${2:-http://localhost:4000/health}"
WEBUI_URL="${3:-http://localhost:9000/health}"
QDRANT_URL="${4:-http://localhost:6333/healthz}"
GATEWAY_URL="${5:-http://localhost:3000}"
ADMIN_TOKEN="${TEAM_AI_PLATFORM_ADMIN_TOKEN:-}"
GATEWAY_API_KEY="${TEAM_AI_PLATFORM_GATEWAY_API_KEY:-${LITELLM_MASTER_KEY:-}}"

if command -v python3 >/dev/null 2>&1; then
	PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
	PYTHON_BIN="python"
else
	echo "[ERROR] python is required for extended checks" >&2
	exit 1
fi

echo "[INFO] Checking backend..."
curl -sS "${BACKEND_URL}" | cat

echo "[INFO] Admin console entrypoint: http://localhost:8000/admin"

echo "[INFO] Checking LiteLLM..."
if [[ -n "${LITELLM_MASTER_KEY:-}" ]]; then
	LITELLM_HEALTH_RAW=$(curl -sS "${LITELLM_URL}" \
		-H "Authorization: Bearer ${LITELLM_MASTER_KEY}")
	echo "${LITELLM_HEALTH_RAW}" | ${PYTHON_BIN} -c '
import json
import sys

payload = json.load(sys.stdin)
healthy = payload.get("healthy_count", 0)
unhealthy = payload.get("unhealthy_count", 0)
unhealthy_items = payload.get("unhealthy_endpoints", []) or []
embedding_only = [
	item for item in unhealthy_items
	if "embedding" in str(item.get("model", "")).lower()
]
blocking = [
	item for item in unhealthy_items
	if "embedding" not in str(item.get("model", "")).lower()
]
print(json.dumps({
	"healthy_count": healthy,
	"unhealthy_count": unhealthy,
	"blocking_unhealthy_count": len(blocking),
	"embedding_false_negative_count": len(embedding_only),
	"blocking_models": [item.get("model") for item in blocking[:5]],
}, ensure_ascii=False))
'
else
	LITELLM_STATUS_CODE=$(curl -sS -o /tmp/team_ai_litellm_health.out -w "%{http_code}" "${LITELLM_URL}")
	if [[ "${LITELLM_STATUS_CODE}" == "200" || "${LITELLM_STATUS_CODE}" == "401" ]]; then
		cat /tmp/team_ai_litellm_health.out | cat
	else
		echo "[ERROR] LiteLLM health check failed with status ${LITELLM_STATUS_CODE}" >&2
		exit 1
	fi
fi

if [[ -n "${LITELLM_MASTER_KEY:-}" ]]; then
	echo ""
	echo "[INFO] Checking LiteLLM models with master key..."
	curl -sS "http://localhost:4000/v1/models" \
		-H "Authorization: Bearer ${LITELLM_MASTER_KEY}" | cat
else
	echo ""
	echo "[WARN] LITELLM_MASTER_KEY is not set; skip /v1/models verification."
fi

echo ""
echo "[INFO] Checking Open WebUI..."
curl -sS "${WEBUI_URL}" | cat || true

echo ""
echo "[INFO] Checking Qdrant..."
curl -sS "${QDRANT_URL}" | cat
echo "[INFO] Qdrant is a backend vector store, not a normal user entrypoint."

echo ""
echo "[INFO] Health checks completed."

echo ""
echo "[INFO] Checking Gateway /health..."
curl -sS "${GATEWAY_URL}/health" | cat

if [[ -n "${ADMIN_TOKEN}" ]]; then
	echo ""
	echo "[INFO] Checking aggregated runtime health (/api/platform/runtime-health)..."
	curl -sS "${GATEWAY_URL}/api/platform/runtime-health" \
		-H "Authorization: Bearer ${ADMIN_TOKEN}" | ${PYTHON_BIN} -c '
import json
import sys

payload = json.load(sys.stdin)
checks = payload.get("checks", []) or []
blocking_failed = [c for c in checks if c.get("blocking") and not c.get("ok")]
print(json.dumps({
		"ok": payload.get("ok"),
		"model_count": payload.get("model_count"),
		"chat_model_count": payload.get("chat_model_count"),
		"embedding_model_count": payload.get("embedding_model_count"),
		"blocking_failed": [c.get("name") for c in blocking_failed],
}, ensure_ascii=False))
'
fi

if [[ -z "${GATEWAY_API_KEY}" ]]; then
  echo "[WARN] TEAM_AI_PLATFORM_GATEWAY_API_KEY or LITELLM_MASTER_KEY is not set; skip gateway API checks."
  exit 0
fi

export GATEWAY_URL
export GATEWAY_API_KEY
export ADMIN_TOKEN

echo ""
echo "[INFO] Running gateway chat/responses/embeddings smoke checks..."
SMOKE_OUTPUT=$(${PYTHON_BIN} - <<'PY'
import json
import os
import urllib.error
import urllib.request

base = os.getenv("GATEWAY_URL", "http://localhost:3000").rstrip("/")
gateway_key = os.getenv("GATEWAY_API_KEY", "").strip()
admin_token = os.getenv("ADMIN_TOKEN", "").strip()


def call(path: str, *, method: str = "GET", token: str | None = None, payload: dict | None = None):
	headers = {}
	if token:
		headers["Authorization"] = f"Bearer {token}"
	data = None
	if payload is not None:
		headers["Content-Type"] = "application/json"
		data = json.dumps(payload).encode("utf-8")
	req = urllib.request.Request(base + path, headers=headers, method=method, data=data)
	with urllib.request.urlopen(req, timeout=40) as resp:
		body = resp.read().decode("utf-8")
		return resp.status, json.loads(body)


results = []
status, models_payload = call("/v1/models", token=gateway_key)
all_models = [m.get("id", "") for m in models_payload.get("data", [])]
chat_models = [m for m in all_models if "embedding" not in m.lower() and "image" not in m.lower()]
results.append(("models", status == 200 and len(all_models) > 0, f"all={len(all_models)} chat={len(chat_models)}"))

chat_ok = True
if chat_models:
	for model in chat_models:
		try:
			status, body = call(
				"/v1/chat/completions",
				method="POST",
				token=gateway_key,
				payload={"model": model, "messages": [{"role": "user", "content": "reply ok"}], "max_tokens": 8},
			)
			if status != 200 or not body.get("choices"):
				chat_ok = False
				break
		except Exception:
			chat_ok = False
			break
results.append(("chat", chat_ok, "all chat models passed" if chat_ok else "failed"))

resp_ok = False
if chat_models:
	status, body = call(
		"/v1/responses",
		method="POST",
		token=gateway_key,
		payload={"model": chat_models[0], "input": "reply ok", "max_output_tokens": 8},
	)
	resp_ok = status == 200 and body.get("object") == "response"
results.append(("responses", resp_ok, "ok" if resp_ok else "failed"))

embed_ok = False
try:
	status, body = call(
		"/v1/embeddings",
		method="POST",
		token=gateway_key,
		payload={"model": "text-embedding-v3", "input": "healthcheck embedding"},
	)
	dim = len((body.get("data") or [{}])[0].get("embedding", []))
	embed_ok = status == 200 and dim > 0
	results.append(("embeddings", embed_ok, f"dim={dim}" if embed_ok else "failed"))
except Exception as exc:
	results.append(("embeddings", False, f"error={exc}"))

if admin_token:
	try:
		status, body = call("/api/skills/search?query=learning", token=admin_token)
		results.append(("skills_search", status == 200 and len(body.get("items", [])) >= 0, f"hits={len(body.get('items', []))}"))
	except Exception as exc:
		results.append(("skills_search", False, f"error={exc}"))
else:
	results.append(("skills_search", True, "skipped (no TEAM_AI_PLATFORM_ADMIN_TOKEN)"))

passed = 0
for name, ok, detail in results:
	if ok:
		passed += 1
	print(("OK" if ok else "FAIL") + "\t" + name + "\t" + detail)
print(f"SUMMARY\t{passed}/{len(results)}")
PY
)

echo "${SMOKE_OUTPUT}"

if echo "${SMOKE_OUTPUT}" | grep -q "^FAIL"; then
  echo "[ERROR] Gateway smoke checks failed." >&2
  exit 1
fi

echo "[INFO] Gateway smoke checks passed."
