"""Tests for Feedback & Audit Log API (Task 8)."""
from fastapi.testclient import TestClient

import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).parents[2])) if str(pathlib.Path(__file__).parents[2]) not in sys.path else None
from backend.app.main import app

client = TestClient(app)


def _register_and_login(username: str, password: str = "Pass1234!") -> str:
    client.post("/api/v1/users/register", json={"username": username, "email": f"{username}@test.com", "password": password})
    resp = client.post("/api/v1/users/login", json={"identity": f"{username}@test.com", "password": password})
    return resp.json()["access_token"]


def test_feedback_crud_and_audit_log():
    token = _register_and_login("fb_user")
    auth = {"Authorization": f"Bearer {token}"}

    # Create feedback for a (dummy) task
    create_resp = client.post("/api/v1/feedbacks/", json={
        "resource_type": "task",
        "resource_id": "task_abc123",
        "content": "This task was handled very well.",
        "rating": 5,
    }, headers=auth)
    assert create_resp.status_code == 201
    fb = create_resp.json()
    fb_id = fb["id"]
    assert fb["rating"] == 5
    assert fb["content"] == "This task was handled very well."

    # List all feedbacks
    list_resp = client.get("/api/v1/feedbacks/", headers=auth)
    assert list_resp.status_code == 200
    assert any(f["id"] == fb_id for f in list_resp.json())

    # Filter by resource_type
    filtered = client.get("/api/v1/feedbacks/?resource_type=task", headers=auth)
    assert all(f["resource_type"] == "task" for f in filtered.json())

    # Filter by resource_id
    by_id = client.get(f"/api/v1/feedbacks/?resource_id=task_abc123", headers=auth)
    assert any(f["id"] == fb_id for f in by_id.json())

    # Get single feedback
    single = client.get(f"/api/v1/feedbacks/{fb_id}", headers=auth)
    assert single.status_code == 200

    # 404 for unknown
    assert client.get("/api/v1/feedbacks/no_such_id", headers=auth).status_code == 404

    # Audit log via feedbacks route — creating a feedback writes audit log
    audit_resp = client.get("/api/v1/feedbacks/audit/logs", headers=auth)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert any(lg["resource_type"] == "feedback" and lg["action"] == "create" for lg in logs)

    # Audit log also accessible via auditlogs endpoint
    audit2 = client.get("/api/v1/auditlogs/", headers=auth)
    assert audit2.status_code == 200
    assert len(audit2.json()) >= 1

    # Filter audit log by resource_type
    audit_filtered = client.get("/api/v1/auditlogs/?resource_type=feedback", headers=auth)
    assert all(lg["resource_type"] == "feedback" for lg in audit_filtered.json())
