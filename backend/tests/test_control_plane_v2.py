from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

# Ensure backend package imports work regardless of pytest invocation cwd.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app


def _create_key(client: TestClient, *, team_id: str, owner_id: str, owner_type: str = "user", alias: str | None = None) -> dict:
    payload = {
        "team_id": team_id,
        "owner_type": owner_type,
        "owner_id": owner_id,
        "alias": alias,
    }
    response = client.post("/api/v1/keys", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_token_enforced_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", "secret-token")
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        no_token_response = client.get("/api/v1/keys")
        assert no_token_response.status_code == 401

        with_header_response = client.get("/api/v1/keys", headers={"X-Admin-Token": "secret-token"})
        assert with_header_response.status_code == 200

        with_bearer_response = client.get("/api/v1/keys", headers={"Authorization": "Bearer secret-token"})
        assert with_bearer_response.status_code == 200


def test_create_and_list_virtual_keys_with_filters(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        first = _create_key(client, team_id="team-alpha", owner_id="u-1", alias="alpha-main")
        second = _create_key(client, team_id="team-beta", owner_id="svc-1", owner_type="service", alias="beta-svc")

        assert first["key"]["status"] == "active"
        assert second["key"]["owner_type"] == "service"
        assert first["key_secret"].startswith("sk-v2-")

        all_keys_response = client.get("/api/v1/keys")
        assert all_keys_response.status_code == 200
        all_keys = all_keys_response.json()
        assert all_keys["total"] >= 2

        filtered_team = client.get("/api/v1/keys", params={"team_id": "team-alpha"}).json()
        assert filtered_team["total"] == 1
        assert filtered_team["items"][0]["team_id"] == "team-alpha"

        filtered_owner_type = client.get("/api/v1/keys", params={"owner_type": "service"}).json()
        assert filtered_owner_type["total"] == 1
        assert filtered_owner_type["items"][0]["owner_id"] == "svc-1"


def test_revoke_and_rotate_virtual_key(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        created = _create_key(client, team_id="team-rotate", owner_id="u-rotate", alias="rot")
        key_id = created["key"]["key_id"]

        revoke_response = client.post(f"/api/v1/keys/{key_id}/revoke")
        assert revoke_response.status_code == 200
        revoked = revoke_response.json()
        assert revoked["status"] == "revoked"
        assert revoked["revoked_at"] is not None

        rotate_response = client.post(f"/api/v1/keys/{key_id}/rotate")
        assert rotate_response.status_code == 200
        rotated = rotate_response.json()
        assert rotated["old_key_id"] == key_id
        assert rotated["new_key"]["key_id"] != key_id
        assert rotated["new_key"]["rotated_from"] == key_id
        assert rotated["new_key_secret"].startswith("sk-v2-")

        old_inactive = client.get("/api/v1/keys", params={"status": "revoked", "team_id": "team-rotate"}).json()
        assert old_inactive["total"] == 1


def test_revoke_and_rotate_missing_key_returns_404(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        revoke_response = client.post("/api/v1/keys/key_not_exist/revoke")
        assert revoke_response.status_code == 404

        rotate_response = client.post("/api/v1/keys/key_not_exist/rotate")
        assert rotate_response.status_code == 404


def test_upsert_and_get_policy(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        created = _create_key(client, team_id="team-policy", owner_id="u-policy")
        key_id = created["key"]["key_id"]

        payload = {
            "allowed_models": ["gpt-5", "claude-sonnet-4"],
            "denied_models": ["gpt-3.5-turbo"],
            "quota_tokens_day": 100000,
            "quota_tokens_month": 3000000,
            "rate_limit_rpm": 120,
            "burst_limit": 30,
            "emergency_block": False,
        }
        upsert_response = client.put(f"/api/v1/policies/keys/{key_id}", json=payload)
        assert upsert_response.status_code == 200
        upserted = upsert_response.json()
        assert upserted["key_id"] == key_id
        assert upserted["allowed_models"] == payload["allowed_models"]

        get_response = client.get(f"/api/v1/policies/keys/{key_id}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["policy_id"] == upserted["policy_id"]
        assert fetched["rate_limit_rpm"] == 120


def test_policy_not_found_paths(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        upsert_response = client.put(
            "/api/v1/policies/keys/key_not_exist",
            json={"allowed_models": ["gpt-5"]},
        )
        assert upsert_response.status_code == 404

        get_response = client.get("/api/v1/policies/keys/key_not_exist")
        assert get_response.status_code == 404


def test_list_ownership_views(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        first = _create_key(client, team_id="team-ops", owner_id="u-ops", owner_type="user", alias="ops-user-1")
        second = _create_key(client, team_id="team-ops", owner_id="u-ops", owner_type="user", alias="ops-user-2")
        _create_key(client, team_id="team-ops", owner_id="svc-ops", owner_type="service", alias="ops-svc")

        key_id = second["key"]["key_id"]
        revoke_response = client.post(f"/api/v1/keys/{key_id}/revoke")
        assert revoke_response.status_code == 200

        ownership_resp = client.get("/api/v1/governance/ownership")
        assert ownership_resp.status_code == 200, ownership_resp.text
        payload = ownership_resp.json()
        assert payload["total"] == 2

        user_owner = [
            item for item in payload["items"]
            if item["team_id"] == "team-ops" and item["owner_type"] == "user" and item["owner_id"] == "u-ops"
        ][0]
        assert user_owner["total_keys"] == 2
        assert user_owner["active_keys"] == 1
        assert user_owner["revoked_keys"] == 1

        filtered_resp = client.get(
            "/api/v1/governance/ownership",
            params={"team_id": "team-ops", "owner_type": "service"},
        )
        assert filtered_resp.status_code == 200
        filtered_payload = filtered_resp.json()
        assert filtered_payload["total"] == 1
        assert filtered_payload["items"][0]["owner_id"] == "svc-ops"
