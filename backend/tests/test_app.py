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
        models = response.json()
        self.assertIsInstance(models, list)
        self.assertTrue(models)
        self.assertEqual(models[0]["id"], "gpt-4o")

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


if __name__ == "__main__":
    unittest.main()
