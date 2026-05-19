from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app


def _register_and_login(client: TestClient, username: str, email: str, password: str) -> str:
    register = client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": password, "role": "member"},
    )
    assert register.status_code == 201, register.text

    login = client.post(
        "/api/v1/users/login",
        json={"identity": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_team_create_invite_update_remove(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)
    monkeypatch.setenv("TEAM_AI_PLATFORM_AUTH_SECRET", "unit-test-secret-team")

    with TestClient(app) as client:
        owner_token = _register_and_login(client, "owner1", "owner1@example.com", "owner1-pass-123")
        member_token = _register_and_login(client, "member1", "member1@example.com", "member1-pass-123")

        create_team = client.post(
            "/api/v1/teams/",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"name": "Core Team", "description": "Main product team"},
        )
        assert create_team.status_code == 201, create_team.text
        team = create_team.json()
        team_id = team["id"]

        list_teams = client.get(
            "/api/v1/teams/",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert list_teams.status_code == 200, list_teams.text
        assert any(item["id"] == team_id for item in list_teams.json())

        invite = client.post(
            f"/api/v1/teams/{team_id}/invite",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": "member1", "role": "member"},
        )
        assert invite.status_code == 201, invite.text

        members = client.get(
            f"/api/v1/teams/{team_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert members.status_code == 200, members.text
        assert any(m["user_id"] == "member1" for m in members.json())

        update_role = client.put(
            f"/api/v1/teams/{team_id}/members/member1/role",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"role": "admin"},
        )
        assert update_role.status_code == 200, update_role.text
        assert update_role.json()["role"] == "admin"

        remove = client.post(
            f"/api/v1/teams/{team_id}/remove",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"user_id": "member1"},
        )
        assert remove.status_code == 204, remove.text

        members_after = client.get(
            f"/api/v1/teams/{team_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert members_after.status_code == 200, members_after.text
        assert all(m["user_id"] != "member1" for m in members_after.json())

        me = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert me.status_code == 200, me.text
