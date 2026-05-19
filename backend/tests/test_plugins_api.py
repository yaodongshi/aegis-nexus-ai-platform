"""Tests for Plugins & Observability API (Task 7)."""
import pytest
from fastapi.testclient import TestClient

import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).parents[2])) if str(pathlib.Path(__file__).parents[2]) not in sys.path else None
from backend.app.main import app

client = TestClient(app)


def _register_and_login(username: str, password: str = "Pass1234!") -> str:
    client.post("/api/v1/users/register", json={"username": username, "email": f"{username}@test.com", "password": password})
    resp = client.post("/api/v1/users/login", json={"identity": f"{username}@test.com", "password": password})
    return resp.json()["access_token"]


def test_plugin_install_update_uninstall():
    token = _register_and_login("plg_user")
    auth = {"Authorization": f"Bearer {token}"}

    # Create a team to install plugin into
    team_resp = client.post("/api/v1/teams/", json={"name": "PlgTeam", "description": ""}, headers=auth)
    assert team_resp.status_code == 201
    team_id = team_resp.json()["id"]

    # Install plugin
    install_resp = client.post("/api/v1/plugins/", json={
        "team_id": team_id,
        "name": "Slack Notifier",
        "description": "Posts alerts to Slack",
        "version": "2.0.0",
        "config": {"webhook_url": "https://hooks.slack.com/xxx"},
    }, headers=auth)
    assert install_resp.status_code == 201
    plugin = install_resp.json()
    plugin_id = plugin["id"]
    assert plugin["enabled"] is True
    assert plugin["name"] == "Slack Notifier"

    # List plugins — should appear
    list_resp = client.get("/api/v1/plugins/", headers=auth)
    assert list_resp.status_code == 200
    assert any(p["id"] == plugin_id for p in list_resp.json())

    # Update plugin config
    update_resp = client.put(f"/api/v1/plugins/{plugin_id}", json={"enabled": False}, headers=auth)
    assert update_resp.status_code == 200
    assert update_resp.json()["enabled"] is False

    # Observability logs — installing should have created a log entry
    log_resp = client.get("/api/v1/plugins/observability/logs", headers=auth)
    assert log_resp.status_code == 200
    logs = log_resp.json()
    assert any(lg["resource_id"] == plugin_id and lg["action"] == "installed" for lg in logs)

    # Uninstall plugin
    del_resp = client.delete(f"/api/v1/plugins/{plugin_id}", headers=auth)
    assert del_resp.status_code == 204

    # After uninstall, 404
    assert client.put(f"/api/v1/plugins/{plugin_id}", json={"enabled": True}, headers=auth).status_code == 404


def test_plugin_team_isolation():
    """User not in a team should not see its plugins."""
    owner_token = _register_and_login("plg_owner")
    other_token = _register_and_login("plg_other")

    owner_auth = {"Authorization": f"Bearer {owner_token}"}
    other_auth = {"Authorization": f"Bearer {other_token}"}

    team_resp = client.post("/api/v1/teams/", json={"name": "IsoTeam", "description": ""}, headers=owner_auth)
    team_id = team_resp.json()["id"]

    client.post("/api/v1/plugins/", json={
        "team_id": team_id,
        "name": "Secret Plugin",
        "version": "1.0.0",
    }, headers=owner_auth)

    # other_user is not in team — should NOT see this plugin
    list_resp = client.get("/api/v1/plugins/", headers=other_auth)
    assert list_resp.status_code == 200
    assert not any(p["name"] == "Secret Plugin" for p in list_resp.json())
