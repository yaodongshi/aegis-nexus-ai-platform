#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DATE_TAG="$(date +%Y-%m-%d)"
LATEST_REPORT="${PROJECT_ROOT}/reports/harness_e2e_acceptance_latest.md"
DATED_REPORT="${PROJECT_ROOT}/reports/harness_e2e_acceptance_${DATE_TAG}.md"

BASE_URL="${HARNESS_BASE_URL:-http://localhost:3000}"
CAPABILITY_ALIAS="${E2E_CAPABILITY_ALIAS:-chat-default}"

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


contract_payload = {
    "contract_version": "v1",
    "runtime_adapter": "local-graph",
    "stable_strategy_id": "strategy-stable-v1",
    "canary_strategy_id": None,
    "canary_traffic_percent": 0,
    "metadata": {
        "risk_level": "p2",
        "requires_approval": False,
        "acceptance_e2e": True,
    },
}

status, contract = api_call(
    "PUT",
    f"/api/v1/harness/capabilities/{capability_alias}",
    contract_payload,
)
expect_ok(status, contract, "upsert capability contract")

status, plan = api_call(
    "POST",
    "/api/v1/harness/plans",
    {
        "capability_alias": capability_alias,
        "metadata": {
            "runtime_adapter": "local-graph",
            "acceptance": "6.2-e2e",
        },
    },
)
expect_ok(status, plan, "create plan")
plan_id = str(plan.get("plan_id"))
trace_id = str(plan.get("trace_id"))

status, run_result = api_call("POST", f"/api/v1/harness/plans/{plan_id}/run", {})
expect_ok(status, run_result, "run plan")

status, completion = api_call(
    "POST",
    f"/api/v1/harness/plans/{plan_id}/events",
    {
        "event_type": "complete",
        "source": "acceptance",
        "payload": {"reason": "e2e acceptance terminal state"},
    },
    trace_id=trace_id,
)
expect_ok(status, completion, "complete plan")

status, trace = api_call("GET", f"/api/v1/harness/traces/{trace_id}")
expect_ok(status, trace, "get trace")

status, replay = api_call(
    "POST",
    f"/api/v1/harness/traces/{trace_id}/replay",
    {"source_plan_id": plan_id, "actor": "acceptance-bot"},
)
expect_ok(status, replay, "replay trace")

rollout_results: list[dict] = []

def rollout(action_payload: dict) -> None:
    status, body = api_call(
        "POST",
        f"/api/v1/harness/capabilities/{capability_alias}/rollout-decisions",
        action_payload,
    )
    expect_ok(status, body, f"rollout {action_payload.get('action')}")
    rollout_results.append(body)


rollout(
    {
        "action": "canary",
        "candidate_strategy_id": "strategy-canary-v2",
        "canary_traffic_percent": 20,
        "actor": "acceptance-bot",
        "rationale": "start canary for e2e acceptance",
    }
)

rollout(
    {
        "action": "promote",
        "actor": "acceptance-bot",
        "rationale": "promote canary strategy after run validation",
    }
)

rollout(
    {
        "action": "canary",
        "candidate_strategy_id": "strategy-canary-v3",
        "canary_traffic_percent": 10,
        "actor": "acceptance-bot",
        "rationale": "stage rollback drill candidate",
    }
)

rollout(
    {
        "action": "rollback",
        "actor": "acceptance-bot",
        "rationale": "rollback drill for acceptance evidence",
    }
)

status, decisions = api_call(
    "GET",
    f"/api/v1/harness/capabilities/{capability_alias}/rollout-decisions",
)
expect_ok(status, decisions, "list rollout decisions")

status, metrics = api_call(
    "GET",
    f"/api/v1/harness/metrics?capability_alias={capability_alias}",
)
expect_ok(status, metrics, "metrics snapshot")

status, alerts = api_call(
    "POST",
    "/api/v1/harness/alerts/evaluate",
    {
        "capability_alias": capability_alias,
        "thresholds": {
            "min_success_rate": 0.5,
            "max_avg_latency_ms": 300.0,
            "max_total_cost_usd": 5.0,
            "max_rollback_rate": 0.5,
        },
    },
)
expect_ok(status, alerts, "alert evaluation")

actions_seen = [item.get("action") for item in decisions]
required_actions = {"promote", "rollback"}
if not required_actions.issubset(set(actions_seen)):
    raise SystemExit(
        f"rollout actions missing in audit list: actions_seen={actions_seen}"
    )

final_contract_status, final_contract = api_call(
    "GET",
    f"/api/v1/harness/capabilities/{capability_alias}",
)
expect_ok(final_contract_status, final_contract, "get final capability contract")

generated_at = datetime.now(UTC).isoformat()

lines = [
    "# Harness E2E Acceptance Report (Task 6.2)",
    "",
    f"- Generated At: {generated_at}",
    f"- Commit: {git_sha}",
    f"- Base URL: {base_url}",
    f"- Capability Alias: {capability_alias}",
    "",
    "## Flow Result",
    "",
    "- create_plan: passed",
    "- run_plan: passed",
    "- complete_plan: passed",
    "- trace_fetch: passed",
    "- replay_trace: passed",
    "- rollout_canary: passed",
    "- rollout_promote: passed",
    "- rollout_rollback: passed",
    "- audit_list_rollout_decisions: passed",
    "",
    "## Runtime IDs",
    "",
    f"- source_plan_id: {plan_id}",
    f"- source_trace_id: {trace_id}",
    f"- replay_plan_id: {replay.get('replay_plan', {}).get('plan_id')}",
    f"- replayed_event_count: {replay.get('replayed_event_count')}",
    "",
    "## Plan States",
    "",
    f"- source_plan_state_after_complete: {completion.get('plan', {}).get('state')}",
    f"- replay_plan_state: {replay.get('replay_plan', {}).get('state')}",
    "",
    "## Rollout Audit",
    "",
    f"- rollout_decision_count: {len(decisions)}",
    f"- actions_seen: {', '.join(actions_seen)}",
    f"- last_decision_id: {decisions[-1].get('decision_id') if decisions else ''}",
    "",
    "## Final Contract",
    "",
    f"- stable_strategy_id: {final_contract.get('stable_strategy_id')}",
    f"- canary_strategy_id: {final_contract.get('canary_strategy_id')}",
    f"- canary_traffic_percent: {final_contract.get('canary_traffic_percent')}",
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

echo "[OK] Harness 6.2 e2e acceptance reports generated:"
echo "- ${LATEST_REPORT}"
echo "- ${DATED_REPORT}"
