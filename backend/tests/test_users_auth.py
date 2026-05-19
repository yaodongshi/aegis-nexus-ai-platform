from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app


def test_register_login_me_and_reset_password(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)
    monkeypatch.setenv("TEAM_AI_PLATFORM_AUTH_SECRET", "unit-test-secret")

    with TestClient(app) as client:
        register = client.post(
            "/api/v1/users/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "alice-pass-123",
                "role": "member",
            },
        )
        assert register.status_code == 201, register.text
        profile = register.json()
        assert profile["username"] == "alice"

        login = client.post(
            "/api/v1/users/login",
            json={"identity": "alice@example.com", "password": "alice-pass-123"},
        )
        assert login.status_code == 200, login.text
        login_payload = login.json()
        token = login_payload["access_token"]
        assert token.startswith("tap_")

        me = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me.status_code == 200, me.text
        assert me.json()["email"] == "alice@example.com"

        reset = client.post(
            "/api/v1/users/reset_password",
            headers={"Authorization": f"Bearer {token}"},
            json={"old_password": "alice-pass-123", "new_password": "alice-pass-456"},
        )
        assert reset.status_code == 204, reset.text

        login_old = client.post(
            "/api/v1/users/login",
            json={"identity": "alice", "password": "alice-pass-123"},
        )
        assert login_old.status_code == 401

        login_new = client.post(
            "/api/v1/users/login",
            json={"identity": "alice", "password": "alice-pass-456"},
        )
        assert login_new.status_code == 200, login_new.text


def test_register_conflict_and_invalid_login(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/users/register",
            json={
                "username": "bob",
                "email": "bob@example.com",
                "password": "bob-pass-123",
                "role": "member",
            },
        )
        assert first.status_code == 201, first.text

        duplicate_email = client.post(
            "/api/v1/users/register",
            json={
                "username": "bob2",
                "email": "bob@example.com",
                "password": "bob-pass-456",
                "role": "member",
            },
        )
        assert duplicate_email.status_code == 409

        bad_login = client.post(
            "/api/v1/users/login",
            json={"identity": "bob@example.com", "password": "wrong-password"},
        )
        assert bad_login.status_code == 401
