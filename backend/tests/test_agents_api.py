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


def _create_team_and_project(client: TestClient, token: str) -> str:
    create_team = client.post(
        "/api/v1/teams/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "AI Team", "description": "Agent work"},
    )
    assert create_team.status_code == 201, create_team.text
    team_id = create_team.json()["id"]

    create_project = client.post(
        "/api/v1/projects/",
        headers={"Authorization": f"Bearer {token}"},
        json={"team_id": team_id, "name": "AI Project", "description": "Agent delivery"},
    )
    assert create_project.status_code == 201, create_project.text
    return create_project.json()["id"]


def test_agent_crud_flow(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)
    monkeypatch.setenv("TEAM_AI_PLATFORM_AUTH_SECRET", "unit-test-secret-agent")

    with TestClient(app) as client:
        token = _register_and_login(client, "agentowner", "agentowner@example.com", "agent-pass-123")
        project_id = _create_team_and_project(client, token)

        create_agent = client.post(
            "/api/v1/agents/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "project_id": project_id,
                "name": "Code Reviewer",
                "description": "Review pull requests",
                "system_prompt": "You are a strict code reviewer.",
                "tags": ["review", "quality"],
            },
        )
        assert create_agent.status_code == 201, create_agent.text
        agent = create_agent.json()
        agent_id = agent["id"]
        assert agent["version"] == 1

        list_agents = client.get(
            "/api/v1/agents/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_agents.status_code == 200, list_agents.text
        assert any(item["id"] == agent_id for item in list_agents.json())

        update = client.put(
            f"/api/v1/agents/{agent_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": "Review PRs and suggest fixes", "status": "active"},
        )
        assert update.status_code == 200, update.text
        updated = update.json()
        assert updated["description"] == "Review PRs and suggest fixes"
        assert updated["version"] == 2

        get_agent = client.get(
            f"/api/v1/agents/{agent_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_agent.status_code == 200, get_agent.text

        delete = client.delete(
            f"/api/v1/agents/{agent_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete.status_code == 204, delete.text

        get_deleted = client.get(
            f"/api/v1/agents/{agent_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_deleted.status_code == 404
