#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DATE_TAG="$(date +%Y-%m-%d)"
LATEST_REPORT="${PROJECT_ROOT}/reports/harness_rollback_drill_latest.md"
DATED_REPORT="${PROJECT_ROOT}/reports/harness_rollback_drill_${DATE_TAG}.md"

BASE_URL="${HARNESS_BASE_URL:-http://localhost:3000}"
CAPABILITY_ALIAS="${ROLLBACK_DRILL_CAPABILITY_ALIAS:-chat-default}"

PYTHON_BIN="${PROJECT_ROOT}/../.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

if [[ -f "${PROJECT_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${PROJECT_ROOT}/.env"
  set +a
fi

mkdir -p "${PROJECT_ROOT}/reports"

pushd "${PROJECT_ROOT}" >/dev/null
GIT_SHA="$(git rev-parse --short HEAD)"
popd >/dev/null

"${PYTHON_BIN}" - <<'PY' "${BASE_URL}" "${CAPABILITY_ALIAS}" "${LATEST_REPORT}" "${DATED_REPORT}" "${GIT_SHA}" "${TEAM_AI_PLATFORM_ADMIN_TOKEN:-}"
from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from urllib import error, request

base_url = sys.argv[1].rstrip("/")
capability_alias = sys.argv[2]
latest_report = Path(sys.argv[3])
dated_report = Path(sys.argv[4])
git_sha = sys.argv[5]
admin_token = sys.argv[6].strip()


def api_call(
    method: str,
    path: str,
    payload: dict | None = None,
    trace_id: str | None = None,
) -> tuple[int, dict]:
    body = None
    headers: dict[str, str] = {}
    if admin_token:
        headers["X-Admin-Token"] = admin_token
    if trace_id:
        headers["X-Trace-Id"] = trace_id
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
        payload_json: dict = {}
        if raw:
            try:
                payload_json = json.loads(raw)
            except Exception:
                payload_json = {"detail": raw}
        return int(exc.code), payload_json


def expect_ok(status: int, body: dict, action: str) -> None:
    if status != 200:
        raise SystemExit(f"{action} failed: status={status} body={body}")


# Ensure deterministic baseline before drill.
contract_payload = {
    "contract_version": "v1",
    "runtime_adapter": "local-graph",
    "stable_strategy_id": "strategy-rollback-stable-v1",
    "canary_strategy_id": None,
    "canary_traffic_percent": 0,
    "metadata": {
        "risk_level": "p2",
        "requires_approval": False,
        "rollback_drill": True,
    },
}
status, contract = api_call(
    "PUT",
    f"/api/v1/harness/capabilities/{capability_alias}",
    contract_payload,
)
expect_ok(status, contract, "upsert rollback drill contract")

initial_stable = contract.get("stable_strategy_id")

status, canary_decision = api_call(
    "POST",
    f"/api/v1/harness/capabilities/{capability_alias}/rollout-decisions",
    {
        "action": "canary",
        "candidate_strategy_id": "strategy-rollback-canary-v2",
        "canary_traffic_percent": 15,
        "actor": "rollback-drill-bot",
        "rationale": "inject canary for rollback drill",
    },
)
expect_ok(status, canary_decision, "create canary decision")

status, rollback_decision = api_call(
    "POST",
    f"/api/v1/harness/capabilities/{capability_alias}/rollout-decisions",
    {
        "action": "rollback",
        "actor": "rollback-drill-bot",
        "rationale": "rollback drill execution",
    },
)
expect_ok(status, rollback_decision, "create rollback decision")

status, final_contract = api_call(
    "GET",
    f"/api/v1/harness/capabilities/{capability_alias}",
)
expect_ok(status, final_contract, "get final contract")

if final_contract.get("stable_strategy_id") != initial_stable:
    raise SystemExit(
        "rollback drill failed: stable strategy changed unexpectedly"
    )
if final_contract.get("canary_strategy_id") not in (None, ""):
    raise SystemExit(
        "rollback drill failed: canary strategy should be cleared"
    )
if int(final_contract.get("canary_traffic_percent") or 0) != 0:
    raise SystemExit(
        "rollback drill failed: canary traffic percent should be 0"
    )

# Build one plan and move it into rolled_back terminal state as runtime evidence.
status, plan = api_call(
    "POST",
    "/api/v1/harness/plans",
    {
        "capability_alias": capability_alias,
        "metadata": {
            "runtime_adapter": "local-graph",
            "rollback_drill": "6.3",
        },
    },
)
expect_ok(status, plan, "create drill plan")
plan_id = str(plan.get("plan_id"))
trace_id = str(plan.get("trace_id"))

status, run_result = api_call("POST", f"/api/v1/harness/plans/{plan_id}/run", {})
expect_ok(status, run_result, "run drill plan")

status, rollback_event = api_call(
    "POST",
    f"/api/v1/harness/plans/{plan_id}/events",
    {
        "event_type": "rollback",
        "source": "rollback-drill",
        "payload": {
            "reason": "forced rollback terminal drill",
            "decision_id": rollback_decision.get("decision_id"),
        },
    },
    trace_id=trace_id,
)
expect_ok(status, rollback_event, "ingest rollback event")

status, trace = api_call("GET", f"/api/v1/harness/traces/{trace_id}")
expect_ok(status, trace, "get drill trace")

status, decisions = api_call(
    "GET",
    f"/api/v1/harness/capabilities/{capability_alias}/rollout-decisions",
)
expect_ok(status, decisions, "list rollout decisions")

status, metrics = api_call(
    "GET",
    f"/api/v1/harness/metrics?capability_alias={capability_alias}",
)
expect_ok(status, metrics, "get metrics")

status, alerts = api_call(
    "POST",
    "/api/v1/harness/alerts/evaluate",
    {
        "capability_alias": capability_alias,
        "thresholds": {
            "min_success_rate": 0.0,
            "max_avg_latency_ms": 1000.0,
            "max_total_cost_usd": 20.0,
            "max_rollback_rate": 1.0,
        },
    },
)
expect_ok(status, alerts, "evaluate alerts")

if rollback_event.get("plan", {}).get("state") != "rolled_back":
    raise SystemExit("rollback event did not drive plan to rolled_back")

rollback_actions = [d for d in decisions if d.get("action") == "rollback"]
if not rollback_actions:
    raise SystemExit("rollback audit evidence missing")

latest_rollback = rollback_actions[-1]

if latest_rollback.get("canary_strategy_after") not in (None, ""):
    raise SystemExit("rollback decision did not clear canary strategy")
if int(latest_rollback.get("canary_traffic_percent_after") or 0) != 0:
    raise SystemExit("rollback decision did not set canary traffic to 0")

trace_event_types = [evt.get("event_type") for evt in trace.get("events") or []]
if "rollback" not in trace_event_types:
    raise SystemExit("rollback event not found in trace evidence")

generated_at = datetime.now(UTC).isoformat()

lines = [
    "# Harness Rollback Drill Report (Task 6.3)",
    "",
    f"- Generated At: {generated_at}",
    f"- Commit: {git_sha}",
    f"- Base URL: {base_url}",
    f"- Capability Alias: {capability_alias}",
    "",
    "## Drill Checks",
    "",
    "- contract_canary_injected: passed",
    "- rollout_rollback_decision: passed",
    "- contract_restored_after_rollback: passed",
    "- plan_rollback_terminal_state: passed",
    "- trace_contains_rollback_event: passed",
    "- audit_contains_rollback_decision: passed",
    "",
    "## Runtime Evidence",
    "",
    f"- plan_id: {plan_id}",
    f"- trace_id: {trace_id}",
    f"- rollback_decision_id: {rollback_decision.get('decision_id')}",
    f"- latest_audit_rollback_decision_id: {latest_rollback.get('decision_id')}",
    "",
    "## Contract Before/After",
    "",
    f"- stable_strategy_before: {initial_stable}",
    f"- stable_strategy_after: {final_contract.get('stable_strategy_id')}",
    f"- canary_strategy_after: {final_contract.get('canary_strategy_id')}",
    f"- canary_traffic_after: {final_contract.get('canary_traffic_percent')}",
    "",
    "## Plan and Trace",
    "",
    f"- plan_state_after_rollback_event: {rollback_event.get('plan', {}).get('state')}",
    f"- trace_event_types: {', '.join(trace_event_types)}",
    "",
    "## Rollout Audit Snapshot",
    "",
    f"- decision_count: {len(decisions)}",
    f"- rollback_decision_count: {len(rollback_actions)}",
    f"- latest_rollback_canary_strategy_after: {latest_rollback.get('canary_strategy_after')}",
    f"- latest_rollback_canary_traffic_percent_after: {latest_rollback.get('canary_traffic_percent_after')}",
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

for item in alerts.get("alerts") or []:
    lines.append(
        "- {code} ({level}): value={value}, threshold={threshold}".format(
            code=item.get("code"),
            level=item.get("level"),
            value=item.get("metric_value"),
            threshold=item.get("threshold_value"),
        )
    )

content = "\n".join(lines) + "\n"
latest_report.write_text(content, encoding="utf-8")
dated_report.write_text(content, encoding="utf-8")

print(str(latest_report))
print(str(dated_report))
PY

echo "[OK] Harness 6.3 rollback drill reports generated:"
echo "- ${LATEST_REPORT}"
echo "- ${DATED_REPORT}"
