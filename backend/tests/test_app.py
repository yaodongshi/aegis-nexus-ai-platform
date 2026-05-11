from __future__ import annotations

from datetime import UTC, datetime
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas import ProviderProbeResponse, ProviderProbeResult


class TestBackendApp(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def test_health_check(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_default_models_seeded(self) -> None:
        response = self.client.get("/api/models")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsInstance(payload, dict)
        self.assertIn("items", payload)
        self.assertIn("total", payload)
        models = payload["items"]
        self.assertTrue(models)
        self.assertEqual(models[0]["id"], "gpt-4o")

    def test_model_filtering(self) -> None:
        response = self.client.get("/api/models", params={"provider": "openai"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        models = payload["items"]
        self.assertTrue(models)
        self.assertTrue(all(model["provider"] == "openai" for model in models))

    def test_model_pagination(self) -> None:
        response = self.client.get("/api/models", params={"limit": 1, "offset": 0})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["limit"], 1)
        self.assertEqual(payload["offset"], 0)
        self.assertGreaterEqual(payload["total"], 1)
        self.assertEqual(len(payload["items"]), 1)

    def test_issue_virtual_key(self) -> None:
        response = self.client.post(
            "/api/keys/issue",
            json={
                "user_id": "u_1001",
                "project_id": "p_ai_platform",
                "scope": "project:read",
                "expire_at": "2026-12-31T23:59:59Z",
                "quota": 1000,
            },
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["status"], "active")
        self.assertTrue(payload["key_secret"].startswith("sk-virtual-"))

    def test_provider_presets_and_create(self) -> None:
        presets_resp = self.client.get("/api/providers/presets")
        self.assertEqual(presets_resp.status_code, 200)
        presets = presets_resp.json()
        self.assertTrue(any(item["key"] == "openai_official" for item in presets))

        app_filter_resp = self.client.get("/api/providers/presets", params={"app": "gemini"})
        self.assertEqual(app_filter_resp.status_code, 200)
        app_filtered = app_filter_resp.json()
        self.assertTrue(app_filtered)
        self.assertTrue(all("gemini" in item["suggested_apps"] for item in app_filtered))

        keyword_filter_resp = self.client.get("/api/providers/presets", params={"q": "deepseek"})
        self.assertEqual(keyword_filter_resp.status_code, 200)
        keyword_filtered = keyword_filter_resp.json()
        self.assertTrue(keyword_filtered)
        self.assertTrue(any("deepseek" in item["key"] for item in keyword_filtered))

        create_resp = self.client.post(
            "/api/providers",
            json={
                "name": "OpenAI Prod",
                "provider_type": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "sk-1234567890abcdef",
                "preset_key": "openai_official",
                "scope": "unified",
                "apps": ["open_webui", "codex"],
                "api_format": "openai",
                "enabled": True,
            },
        )
        self.assertEqual(create_resp.status_code, 201)
        provider = create_resp.json()
        self.assertEqual(provider["name"], "OpenAI Prod")
        self.assertEqual(provider["scope"], "unified")
        self.assertEqual(provider["api_key_masked"], "sk-1...cdef")

        list_resp = self.client.get("/api/providers", params={"app": "open_webui"})
        self.assertEqual(list_resp.status_code, 200)
        payload = list_resp.json()
        self.assertGreaterEqual(payload["total"], 1)
        self.assertTrue(payload["items"])

    def test_provider_console_page(self) -> None:
        response = self.client.get("/provider-console")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Provider Console", response.text)

    def test_provider_update_enabled(self) -> None:
        create_resp = self.client.post(
            "/api/providers",
            json={
                "name": "Toggle Provider",
                "provider_type": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "sk-toggle-12345678",
                "scope": "app",
                "apps": ["open_webui"],
                "api_format": "openai",
                "enabled": True,
            },
        )
        self.assertEqual(create_resp.status_code, 201)
        provider_id = create_resp.json()["id"]

        patch_resp = self.client.patch(f"/api/providers/{provider_id}", json={"enabled": False})
        self.assertEqual(patch_resp.status_code, 200)
        self.assertFalse(patch_resp.json()["enabled"])

        get_resp = self.client.get(f"/api/providers/{provider_id}")
        self.assertEqual(get_resp.status_code, 200)
        self.assertFalse(get_resp.json()["enabled"])

    def test_provider_probe_endpoint(self) -> None:
        create_resp = self.client.post(
            "/api/providers",
            json={
                "name": "Probe Provider",
                "provider_type": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "sk-probe-12345678",
                "scope": "app",
                "apps": ["open_webui"],
                "api_format": "openai",
                "enabled": True,
            },
        )
        self.assertEqual(create_resp.status_code, 201)
        provider_id = create_resp.json()["id"]

        fake_response = ProviderProbeResponse(
            provider_id=provider_id,
            best_endpoint="https://fast.example.com",
            results=[
                ProviderProbeResult(endpoint="https://slow.example.com", ok=True, status_code=200, latency_ms=800),
                ProviderProbeResult(endpoint="https://fast.example.com", ok=True, status_code=200, latency_ms=120),
            ],
            probed_at=datetime.now(UTC),
        )

        with patch("backend.app.store.PlatformStore.probe_provider_endpoints", return_value=fake_response):
            probe_resp = self.client.post(
                f"/api/providers/{provider_id}/probe",
                json={"endpoints": ["https://slow.example.com", "https://fast.example.com"], "timeout_ms": 3000},
            )

        self.assertEqual(probe_resp.status_code, 200)
        payload = probe_resp.json()
        self.assertEqual(payload["best_endpoint"], "https://fast.example.com")
        self.assertEqual(len(payload["results"]), 2)

    def test_provider_probe_history_endpoint(self) -> None:
        create_resp = self.client.post(
            "/api/providers",
            json={
                "name": "History Provider",
                "provider_type": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "sk-history-123456",
                "scope": "app",
                "apps": ["open_webui"],
                "api_format": "openai",
                "enabled": True,
            },
        )
        provider_id = create_resp.json()["id"]

        with patch("backend.app.store.PlatformStore.list_provider_probe_logs", return_value=[]):
            history_resp = self.client.get(f"/api/providers/{provider_id}/probe-history", params={"limit": 5})

        self.assertEqual(history_resp.status_code, 200)
        self.assertEqual(history_resp.json(), [])

    def test_provider_probe_all_endpoint(self) -> None:
        create_resp = self.client.post(
            "/api/providers",
            json={
                "name": "Batch Probe Provider",
                "provider_type": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "sk-batch-123456",
                "scope": "app",
                "apps": ["open_webui"],
                "api_format": "openai",
                "enabled": True,
            },
        )
        provider_id = create_resp.json()["id"]

        with patch("backend.app.store.PlatformStore.batch_probe_providers") as mocked:
            mocked.return_value = {
                "items": [
                    {
                        "provider_id": provider_id,
                        "provider_name": "Batch Probe Provider",
                        "best_endpoint": "https://api.openai.com",
                        "applied": False,
                        "results": [
                            {
                                "endpoint": "https://api.openai.com",
                                "ok": True,
                                "status_code": 200,
                                "latency_ms": 150,
                                "error": None,
                            }
                        ],
                    }
                ],
                "total": 1,
                "succeeded": 1,
                "probed_at": datetime.now(UTC).isoformat(),
            }
            batch_resp = self.client.post(
                "/api/providers/probe-all",
                json={"provider_ids": [provider_id], "timeout_ms": 5000, "apply_best_endpoint": False},
            )

        self.assertEqual(batch_resp.status_code, 200)
        payload = batch_resp.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["succeeded"], 1)

    def test_provider_batch_update_endpoint(self) -> None:
        first = self.client.post(
            "/api/providers",
            json={
                "name": "Batch Update A",
                "provider_type": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "sk-update-a-123",
                "scope": "app",
                "apps": ["open_webui"],
                "api_format": "openai",
                "enabled": True,
            },
        )
        second = self.client.post(
            "/api/providers",
            json={
                "name": "Batch Update B",
                "provider_type": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "sk-update-b-123",
                "scope": "app",
                "apps": ["open_webui"],
                "api_format": "openai",
                "enabled": True,
            },
        )
        p1 = first.json()["id"]
        p2 = second.json()["id"]

        batch_resp = self.client.post(
            "/api/providers/batch-update",
            json={
                "provider_ids": [p1, p2],
                "enabled": False,
                "target_apps": ["open_webui", "codex"],
                "force_unified": True,
            },
        )
        self.assertEqual(batch_resp.status_code, 200)
        payload = batch_resp.json()
        self.assertEqual(payload["updated"], 2)

        verify = self.client.get(f"/api/providers/{p1}")
        self.assertEqual(verify.status_code, 200)
        self.assertFalse(verify.json()["enabled"])
        self.assertEqual(verify.json()["scope"], "unified")
        self.assertEqual(verify.json()["apps"], ["open_webui", "codex"])

    def test_provider_batch_delete_endpoint(self) -> None:
        first = self.client.post(
            "/api/providers",
            json={
                "name": "Batch Delete A",
                "provider_type": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "sk-delete-a-123",
                "scope": "app",
                "apps": ["open_webui"],
                "api_format": "openai",
                "enabled": True,
            },
        )
        second = self.client.post(
            "/api/providers",
            json={
                "name": "Batch Delete B",
                "provider_type": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "sk-delete-b-123",
                "scope": "app",
                "apps": ["open_webui"],
                "api_format": "openai",
                "enabled": True,
            },
        )
        p1 = first.json()["id"]
        p2 = second.json()["id"]

        batch_resp = self.client.post("/api/providers/batch-delete", json={"provider_ids": [p1, p2]})
        self.assertEqual(batch_resp.status_code, 200)
        payload = batch_resp.json()
        self.assertEqual(payload["deleted"], 2)

        verify_deleted = self.client.get(f"/api/providers/{p1}")
        self.assertEqual(verify_deleted.status_code, 404)

    def test_admin_token_required_for_provider_api_when_configured(self) -> None:
        with patch.dict("os.environ", {"TEAM_AI_PLATFORM_ADMIN_TOKEN": "admin-token-1"}):
            denied_resp = self.client.get("/api/providers", params={"limit": 1, "offset": 0})
            self.assertEqual(denied_resp.status_code, 401)

            allowed_resp = self.client.get(
                "/api/providers",
                params={"limit": 1, "offset": 0},
                headers={"X-Admin-Token": "admin-token-1"},
            )
            self.assertEqual(allowed_resp.status_code, 200)

    def test_admin_token_required_for_keys_api_when_configured(self) -> None:
        with patch.dict("os.environ", {"TEAM_AI_PLATFORM_ADMIN_TOKEN": "admin-token-2"}):
            denied_resp = self.client.get("/api/keys", params={"limit": 1, "offset": 0})
            self.assertEqual(denied_resp.status_code, 401)

            allowed_resp = self.client.get(
                "/api/keys",
                params={"limit": 1, "offset": 0},
                headers={"X-Admin-Token": "admin-token-2"},
            )
            self.assertEqual(allowed_resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
