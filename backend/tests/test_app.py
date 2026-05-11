from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from backend.app.main import app


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


if __name__ == "__main__":
    unittest.main()
