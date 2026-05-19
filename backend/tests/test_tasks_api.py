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


def _create_project(client: TestClient, token: str) -> str:
    create_team = client.post(
        "/api/v1/teams/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Task Team", "description": "Task team"},
    )
    assert create_team.status_code == 201, create_team.text
    team_id = create_team.json()["id"]

    create_project = client.post(
        "/api/v1/projects/",
        headers={"Authorization": f"Bearer {token}"},
        json={"team_id": team_id, "name": "Task Project", "description": "Task flow"},
    )
    assert create_project.status_code == 201, create_project.text
    return create_project.json()["id"]


def test_task_flow_with_comments_and_history(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)
    monkeypatch.setenv("TEAM_AI_PLATFORM_AUTH_SECRET", "unit-test-secret-task")

    with TestClient(app) as client:
        token = _register_and_login(client, "taskowner", "taskowner@example.com", "task-pass-123")
        project_id = _create_project(client, token)

        create_task = client.post(
            "/api/v1/tasks/",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "project_id": project_id,
                "title": "Implement workflow",
                "description": "Build full task lifecycle",
                "priority": "high",
            },
        )
        assert create_task.status_code == 201, create_task.text
        task_id = create_task.json()["id"]

        update = client.put(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "in_progress", "assignee_id": "taskowner"},
        )
        assert update.status_code == 200, update.text
        assert update.json()["status"] == "in_progress"

        comment = client.post(
            f"/api/v1/tasks/{task_id}/comments",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": "Started implementing API endpoints."},
        )
        assert comment.status_code == 201, comment.text

        comments = client.get(
            f"/api/v1/tasks/{task_id}/comments",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert comments.status_code == 200, comments.text
        assert len(comments.json()) == 1

        history = client.get(
            f"/api/v1/tasks/{task_id}/history",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert history.status_code == 200, history.text
        actions = [item["action"] for item in history.json()]
        assert "created" in actions
        assert "status_changed" in actions
        assert "commented" in actions
