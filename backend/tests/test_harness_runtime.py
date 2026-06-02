from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def test_plan_inherits_capability_contract(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        upsert_resp = client.put(
            "/api/v1/harness/capabilities/chat-default",
            json={
                "contract_version": "v2",
                "runtime_adapter": "noop",
                "stable_strategy_id": "strategy-chat-stable",
                "canary_traffic_percent": 0,
            },
        )
        assert upsert_resp.status_code == 200, upsert_resp.text

        create_plan_resp = client.post(
            "/api/v1/harness/plans",
            json={
                "capability_alias": "chat-default",
                "metadata": {"source": "tests"},
            },
        )
        assert create_plan_resp.status_code == 200, create_plan_resp.text
        created = create_plan_resp.json()
        assert created["strategy_id"] == "strategy-chat-stable"
        assert created["metadata"]["runtime_adapter"] == "noop"
        assert created["metadata"]["capability_contract_version"] == "v2"
        assert (
            created["metadata"]["rollout"]["stable_strategy_id"]
            == "strategy-chat-stable"
        )


def test_trace_id_is_preserved_on_harness_requests(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        trace_id = "trace-unit-test-001"
        upsert_resp = client.put(
            "/api/v1/harness/capabilities/trace-default",
            headers={"X-Trace-Id": trace_id},
            json={
                "contract_version": "v1",
                "runtime_adapter": "noop",
                "stable_strategy_id": "strategy-trace-v1",
                "canary_traffic_percent": 0,
            },
        )
        assert upsert_resp.status_code == 200, upsert_resp.text

        create_plan_resp = client.post(
            "/api/v1/harness/plans",
            headers={"X-Trace-Id": trace_id},
            json={
                "capability_alias": "trace-default",
            },
        )
        assert create_plan_resp.status_code == 200, create_plan_resp.text
        assert create_plan_resp.headers["X-Trace-Id"] == trace_id

        created = create_plan_resp.json()
        trace_resp = client.get(f"/api/v1/harness/traces/{trace_id}")
        assert trace_resp.status_code == 200, trace_resp.text
        assert trace_resp.headers["X-Trace-Id"] == trace_id
        assert trace_resp.json()["trace_id"] == trace_id
        assert trace_resp.json()["plans"][0]["plan_id"] == created["plan_id"]


def test_rollout_decision_canary_then_promote(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        upsert_resp = client.put(
            "/api/v1/harness/capabilities/embed-default",
            json={
                "contract_version": "v1",
                "runtime_adapter": "noop",
                "stable_strategy_id": "strategy-embed-v1",
                "canary_traffic_percent": 0,
            },
        )
        assert upsert_resp.status_code == 200, upsert_resp.text

        canary_resp = client.post(
            "/api/v1/harness/capabilities/embed-default/rollout-decisions",
            json={
                "action": "canary",
                "candidate_strategy_id": "strategy-embed-v2",
                "canary_traffic_percent": 10,
                "actor": "qa-bot",
                "rationale": "canary baseline healthy",
            },
        )
        assert canary_resp.status_code == 200, canary_resp.text

        contract_after_canary = client.get(
            "/api/v1/harness/capabilities/embed-default"
        )
        assert (
            contract_after_canary.status_code == 200
        ), contract_after_canary.text
        after_canary = contract_after_canary.json()
        assert after_canary["stable_strategy_id"] == "strategy-embed-v1"
        assert after_canary["canary_strategy_id"] == "strategy-embed-v2"
        assert after_canary["canary_traffic_percent"] == 10

        promote_resp = client.post(
            "/api/v1/harness/capabilities/embed-default/rollout-decisions",
            json={
                "action": "promote",
                "actor": "qa-bot",
                "rationale": "promote after canary win",
            },
        )
        assert promote_resp.status_code == 200, promote_resp.text

        contract_after_promote = client.get(
            "/api/v1/harness/capabilities/embed-default"
        )
        assert (
            contract_after_promote.status_code == 200
        ), contract_after_promote.text
        after_promote = contract_after_promote.json()
        assert after_promote["stable_strategy_id"] == "strategy-embed-v2"
        assert after_promote["canary_strategy_id"] is None
        assert after_promote["canary_traffic_percent"] == 0

        decisions_resp = client.get(
            "/api/v1/harness/capabilities/embed-default/rollout-decisions"
        )
        assert decisions_resp.status_code == 200, decisions_resp.text
        decisions = decisions_resp.json()
        assert len(decisions) == 2
        assert decisions[0]["action"] == "canary"
        assert decisions[1]["action"] == "promote"


def test_rollout_promote_without_candidate_conflicts(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        upsert_resp = client.put(
            "/api/v1/harness/capabilities/reasoning-default",
            json={
                "contract_version": "v1",
                "runtime_adapter": "noop",
                "stable_strategy_id": "strategy-reasoning-v1",
                "canary_traffic_percent": 0,
            },
        )
        assert upsert_resp.status_code == 200, upsert_resp.text

        promote_resp = client.post(
            "/api/v1/harness/capabilities/reasoning-default/rollout-decisions",
            json={
                "action": "promote",
                "actor": "qa-bot",
                "rationale": "missing candidate",
            },
        )
        assert promote_resp.status_code == 409


def test_rollout_requires_approval_and_accepts_approved_gate(
    monkeypatch,
) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        upsert_resp = client.put(
            "/api/v1/harness/capabilities/chat-default",
            json={
                "contract_version": "v1",
                "runtime_adapter": "noop",
                "stable_strategy_id": "strategy-chat-v1",
                "canary_traffic_percent": 0,
                "metadata": {
                    "requires_approval": True,
                },
            },
        )
        assert upsert_resp.status_code == 200, upsert_resp.text

        blocked_resp = client.post(
            "/api/v1/harness/capabilities/chat-default/rollout-decisions",
            json={
                "action": "promote",
                "actor": "operator-a",
                "rationale": "needs approval",
            },
        )
        assert blocked_resp.status_code == 403

        approval_resp = client.post(
            "/api/approvals/submit",
            json={
                "applicant_id": "operator-a",
                "action": "harness.rollout.promote",
                "resource_id": "chat-default",
                "reason": "high-risk promotion",
            },
        )
        assert approval_resp.status_code == 201, approval_resp.text
        approval_id = approval_resp.json()["id"]

        still_blocked_resp = client.post(
            "/api/v1/harness/capabilities/chat-default/rollout-decisions",
            json={
                "action": "promote",
                "candidate_strategy_id": "strategy-chat-v2",
                "approval_id": approval_id,
                "actor": "operator-a",
                "rationale": "pending approval",
            },
        )
        assert still_blocked_resp.status_code == 403

        approve_resp = client.post(
            f"/api/approvals/{approval_id}/approve",
            json={"approver_id": "admin", "reason": "approved for rollout"},
        )
        assert approve_resp.status_code == 200, approve_resp.text

        allowed_resp = client.post(
            "/api/v1/harness/capabilities/chat-default/rollout-decisions",
            json={
                "action": "promote",
                "candidate_strategy_id": "strategy-chat-v2",
                "approval_id": approval_id,
                "actor": "operator-a",
                "rationale": "approved rollout",
            },
        )
        assert allowed_resp.status_code == 200, allowed_resp.text
        decision = allowed_resp.json()
        assert decision["approval_id"] == approval_id
        assert decision["approval_status"] == "approved"
