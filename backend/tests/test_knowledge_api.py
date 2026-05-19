"""Tests for Knowledge API (Task 6)."""
import pytest
from fastapi.testclient import TestClient

import sys as _sys
import pathlib as _pathlib
_root = str(_pathlib.Path(__file__).resolve().parents[2])
if _root not in _sys.path:
    _sys.path.insert(0, _root)
from backend.app.main import app


def _register_and_login(client: TestClient, username: str, password: str = "Pass1234!") -> str:
    client.post("/api/v1/users/register", json={"username": username, "email": f"{username}@test.com", "password": password})
    resp = client.post("/api/v1/users/login", json={"identity": f"{username}@test.com", "password": password})
    return resp.json()["access_token"]


def test_knowledge_crud_and_search():
    with TestClient(app) as client:
        token = _register_and_login(client, "kn_user")
        auth = {"Authorization": f"Bearer {token}"}

        # Create a team and project so we have a valid project_id
        team_resp = client.post("/api/v1/teams/", json={"name": "KnTeam", "description": ""}, headers=auth)
        assert team_resp.status_code == 201
        team_id = team_resp.json()["id"]

        proj_resp = client.post("/api/v1/projects/", json={"name": "KnProject", "team_id": team_id, "description": ""}, headers=auth)
        assert proj_resp.status_code == 201
        project_id = proj_resp.json()["id"]

        # Create a knowledge doc
        create_resp = client.post("/api/v1/knowledge/", json={
            "project_id": project_id,
            "title": "How to Deploy",
            "content": "Run docker compose up -d",
            "format": "markdown",
            "tags": ["devops"],
        }, headers=auth)
        assert create_resp.status_code == 201
        doc = create_resp.json()
        doc_id = doc["id"]
        assert doc["version"] == 1
        assert doc["title"] == "How to Deploy"

        # Get single doc
        get_resp = client.get(f"/api/v1/knowledge/{doc_id}", headers=auth)
        assert get_resp.status_code == 200

        # Full-text search — match
        search_resp = client.get("/api/v1/knowledge/?q=Docker", headers=auth)
        assert search_resp.status_code == 200
        assert any(d["id"] == doc_id for d in search_resp.json())

        # Full-text search — no match
        no_match = client.get("/api/v1/knowledge/?q=xyzzyqwerty", headers=auth)
        assert no_match.status_code == 200
        assert all(d["id"] != doc_id for d in no_match.json())

        # Update triggers version bump
        update_resp = client.put(f"/api/v1/knowledge/{doc_id}", json={"content": "Updated content"}, headers=auth)
        assert update_resp.status_code == 200
        assert update_resp.json()["version"] == 2

        # Status change (non-content field) does NOT bump version
        status_resp = client.put(f"/api/v1/knowledge/{doc_id}", json={"status": "archived"}, headers=auth)
        assert status_resp.json()["version"] == 2

        # Delete
        del_resp = client.delete(f"/api/v1/knowledge/{doc_id}", headers=auth)
        assert del_resp.status_code == 204

        # After delete, 404
        assert client.get(f"/api/v1/knowledge/{doc_id}", headers=auth).status_code == 404
