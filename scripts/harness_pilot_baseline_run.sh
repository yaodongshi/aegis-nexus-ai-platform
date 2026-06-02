#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

OUTPUT_PATH="${1:-${PROJECT_ROOT}/reports/harness_pilot_baseline_latest.md}"
BASE_URL="${HARNESS_BASE_URL:-http://localhost:3000}"
CAPABILITY_ALIAS="${PILOT_CAPABILITY_ALIAS:-chat-default}"
RUN_COUNT="${PILOT_RUN_COUNT:-5}"

PYTHON_BIN="${PROJECT_ROOT}/../.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
    PYTHON_BIN="python3"
fi

mkdir -p "$(dirname "${OUTPUT_PATH}")"

if [[ -f "${PROJECT_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${PROJECT_ROOT}/.env"
  set +a
fi

pushd "${PROJECT_ROOT}" >/dev/null
GIT_SHA="$(git rev-parse --short HEAD)"
popd >/dev/null

"${PYTHON_BIN}" - <<'PY' "${BASE_URL}" "${CAPABILITY_ALIAS}" "${RUN_COUNT}" "${OUTPUT_PATH}" "${GIT_SHA}" "${TEAM_AI_PLATFORM_ADMIN_TOKEN:-}"
from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from urllib import error, request

base_url = sys.argv[1].rstrip("/")
capability_alias = sys.argv[2]
run_count = int(sys.argv[3])
output_path = Path(sys.argv[4])
git_sha = sys.argv[5]
admin_token = sys.argv[6].strip()


def api_call(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    body = None
    headers: dict[str, str] = {}
    if admin_token:
        headers["X-Admin-Token"] = admin_token
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(
        f"{base_url}{path}",
        method=method,
        data=body,
        headers=headers,
    )
    try:
        with request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return int(getattr(resp, "status", 200)), json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        payload_json = {}
        if raw:
            try:
                payload_json = json.loads(raw)
            except Exception:
                payload_json = {"detail": raw}
        return int(exc.code), payload_json


contract_payload = {
    "contract_version": "v1",
    "runtime_adapter": "local-graph",
    "stable_strategy_id": "strategy-pilot-v1",
    "canary_traffic_percent": 0,
    "metadata": {"risk_level": "p2", "pilot": True},
}

status, body = api_call(
    "PUT",
    f"/api/v1/harness/capabilities/{capability_alias}",
    contract_payload,
)
if status != 200:
    raise SystemExit(
        f"Failed to upsert capability contract: status={status} body={body}"
    )

runs: list[dict] = []
for idx in range(run_count):
    trace_id = f"pilot-{capability_alias}-{idx+1}"
    create_payload = {
        "capability_alias": capability_alias,
        "metadata": {"pilot_run": True, "batch_index": idx + 1},
    }
    create_status, created = api_call(
        "POST",
        "/api/v1/harness/plans",
        create_payload,
    )
    if create_status != 200:
        raise SystemExit(
            f"Failed to create plan: status={create_status} body={created}"
        )

    plan_id = str(created.get("plan_id", ""))
    run_status, run_body = api_call(
        "POST",
        f"/api/v1/harness/plans/{plan_id}/run",
        {},
    )
    if run_status != 200:
        raise SystemExit(
            f"Failed to run plan {plan_id}: status={run_status} body={run_body}"
        )

    plan = run_body.get("plan") or {}
    adapter_output = run_body.get("adapter_output") or {}
    runs.append(
        {
            "plan_id": plan_id,
            "trace_id": str(plan.get("trace_id", trace_id)),
            "state": str(plan.get("state", "unknown")),
            "latency_ms": adapter_output.get("latency_ms"),
            "cost_usd": adapter_output.get("cost_usd"),
        }
    )

metrics_status, metrics = api_call(
    "GET",
    f"/api/v1/harness/metrics?capability_alias={capability_alias}",
)
if metrics_status != 200:
    raise SystemExit(
        f"Failed to get metrics: status={metrics_status} body={metrics}"
    )

alerts_status, alerts = api_call(
    "POST",
    "/api/v1/harness/alerts/evaluate",
    {
        "capability_alias": capability_alias,
        "thresholds": {
            "min_success_rate": 0.9,
            "max_avg_latency_ms": 300.0,
            "max_total_cost_usd": 2.0,
            "max_rollback_rate": 0.1,
        },
    },
)
if alerts_status != 200:
    raise SystemExit(
        f"Failed to evaluate alerts: status={alerts_status} body={alerts}"
    )

generated_at = datetime.now(UTC).isoformat()

lines = [
    "# Harness Pilot Baseline Report",
    "",
    f"- Generated At: {generated_at}",
    f"- Commit: {git_sha}",
    f"- Base URL: {base_url}",
    f"- Capability Alias: {capability_alias}",
    f"- Pilot Run Count: {run_count}",
    "",
    "## Run Details",
    "",
    "| Plan ID | Trace ID | Final State | Latency(ms) | Cost(USD) |",
    "| --- | --- | --- | --- | --- |",
]

for item in runs:
    lines.append(
        "| {plan_id} | {trace_id} | {state} | {latency} | {cost} |".format(
            plan_id=item["plan_id"],
            trace_id=item["trace_id"],
            state=item["state"],
            latency=item["latency_ms"],
            cost=item["cost_usd"],
        )
    )

lines.extend(
    [
        "",
        "## Metrics Snapshot",
        "",
        f"- plan_total: {metrics.get('plan_total')}",
        f"- terminal_total: {metrics.get('terminal_total')}",
        f"- completed_total: {metrics.get('completed_total')}",
        f"- failed_total: {metrics.get('failed_total')}",
        f"- rolled_back_total: {metrics.get('rolled_back_total')}",
        f"- success_rate: {metrics.get('success_rate')}",
        f"- rollback_rate: {metrics.get('rollback_rate')}",
        f"- avg_latency_ms: {metrics.get('avg_latency_ms')}",
        f"- p95_latency_ms: {metrics.get('p95_latency_ms')}",
        f"- total_cost_usd: {metrics.get('total_cost_usd')}",
        "",
        "## Alert Evaluation",
        "",
        f"- status: {alerts.get('status')}",
        f"- alert_count: {len(alerts.get('alerts') or [])}",
    ]
)

for item in alerts.get("alerts") or []:
    lines.append(
        "- {code} ({level}): value={value}, threshold={threshold}".format(
            code=item.get("code"),
            level=item.get("level"),
            value=item.get("metric_value"),
            threshold=item.get("threshold_value"),
        )
    )

output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(str(output_path))
PY

echo "[OK] Pilot baseline report generated: ${OUTPUT_PATH}"
