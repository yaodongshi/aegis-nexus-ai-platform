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


def test_project_and_repo_flow(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)
    monkeypatch.setenv("TEAM_AI_PLATFORM_AUTH_SECRET", "unit-test-secret-project")

    with TestClient(app) as client:
        owner_token = _register_and_login(client, "owner2", "owner2@example.com", "owner2-pass-123")

        create_team = client.post(
            "/api/v1/teams/",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"name": "Delivery Team", "description": "Project and repo delivery"},
        )
        assert create_team.status_code == 201, create_team.text
        team_id = create_team.json()["id"]

        create_project = client.post(
            "/api/v1/projects/",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"team_id": team_id, "name": "Platform Upgrade", "description": "MVP"},
        )
        assert create_project.status_code == 201, create_project.text
        project = create_project.json()
        project_id = project["id"]

        get_project = client.get(
            f"/api/v1/projects/{project_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert get_project.status_code == 200, get_project.text

        create_repo = client.post(
            "/api/v1/repos/",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "project_id": project_id,
                "name": "backend-core",
                "url": "https://example.com/backend-core.git",
                "default_branch": "main",
            },
        )
        assert create_repo.status_code == 201, create_repo.text
        repo_id = create_repo.json()["id"]

        switch_branch = client.post(
            f"/api/v1/repos/{repo_id}/switch-branch",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"branch": "release/v1"},
        )
        assert switch_branch.status_code == 200, switch_branch.text
        assert switch_branch.json()["current_branch"] == "release/v1"

        sync = client.post(
            f"/api/v1/repos/{repo_id}/sync",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert sync.status_code == 200, sync.text
        assert sync.json()["sync_status"] == "synced"

        list_repos = client.get(
            "/api/v1/repos/",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert list_repos.status_code == 200, list_repos.text
        assert any(item["id"] == repo_id for item in list_repos.json())
