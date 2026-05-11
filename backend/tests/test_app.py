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


if __name__ == "__main__":
    unittest.main()
