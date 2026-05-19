"""Tests for Settings & i18n API (Task 9)."""
from fastapi.testclient import TestClient

import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).parents[2])) if str(pathlib.Path(__file__).parents[2]) not in sys.path else None
from backend.app.main import app

client = TestClient(app)


def _register_and_login(username: str, password: str = "Pass1234!") -> str:
    client.post("/api/v1/users/register", json={"username": username, "email": f"{username}@test.com", "password": password})
    resp = client.post("/api/v1/users/login", json={"identity": f"{username}@test.com", "password": password})
    return resp.json()["access_token"]


def test_user_settings_crud():
    token = _register_and_login("settings_user")
    auth = {"Authorization": f"Bearer {token}"}

    # Default settings
    get_resp = client.get("/api/v1/settings/me", headers=auth)
    assert get_resp.status_code == 200
    defaults = get_resp.json()
    assert defaults["language"] == "zh-CN"
    assert defaults["theme"] == "light"

    # Update settings
    update_resp = client.put("/api/v1/settings/me", json={"theme": "dark", "language": "en-US"}, headers=auth)
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["theme"] == "dark"
    assert updated["language"] == "en-US"

    # Verify persisted
    check = client.get("/api/v1/settings/me", headers=auth)
    assert check.json()["theme"] == "dark"


def test_locales_and_translations():
    token = _register_and_login("locale_user")
    auth = {"Authorization": f"Bearer {token}"}

    # List supported locales (no auth required by spec, but auth still accepted)
    locales_resp = client.get("/api/v1/settings/locales")
    assert locales_resp.status_code == 200
    codes = [loc["code"] for loc in locales_resp.json()]
    assert "zh-CN" in codes
    assert "en-US" in codes

    # Get zh-CN translations
    zh_resp = client.get("/api/v1/settings/translations/zh-CN")
    assert zh_resp.status_code == 200
    zh_data = zh_resp.json()
    assert zh_data["locale"] == "zh-CN"
    assert "common.save" in zh_data["translations"]
    assert zh_data["translations"]["common.save"] == "保存"

    # Get en-US translations
    en_resp = client.get("/api/v1/settings/translations/en-US")
    assert en_resp.status_code == 200
    assert en_resp.json()["translations"]["nav.dashboard"] == "Dashboard"

    # Unknown locale falls back gracefully (returns en-US translations)
    unk_resp = client.get("/api/v1/settings/translations/xx-XX")
    assert unk_resp.status_code == 200
    assert "common.save" in unk_resp.json()["translations"]
