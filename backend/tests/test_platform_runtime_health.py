from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routers import platform as platform_router


def test_runtime_health_chat_probe_fallback(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("LITELLM_MASTER_KEY", "mk-test")
    monkeypatch.setenv("LITELLM_INTERNAL_BASE_URL", "http://litellm.test:4000")

    def fake_call_json(
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        payload: dict | None = None,
        timeout: int = 5,
    ) -> tuple[int, dict]:
        del method, headers, timeout
        if url.endswith("/v1/models"):
            return (
                200,
                {
                    "data": [
                        {"id": "chat-default"},
                        {"id": "gpt-4o"},
                        {"id": "text-embedding-v3"},
                    ]
                },
            )

        if url.endswith("/v1/chat/completions"):
            model = str((payload or {}).get("model", ""))
            if model == "chat-default":
                return 401, {"error": {"message": "unauthorized"}}
            return 200, {"choices": [{"message": {"content": "ok"}}]}

        if url.endswith("/v1/embeddings"):
            return (
                200,
                {
                    "data": [
                        {
                            "embedding": [0.0] * 1024,
                        }
                    ]
                },
            )

        return 500, {"detail": "unexpected"}

    monkeypatch.setattr(platform_router, "_call_json", fake_call_json)

    with TestClient(app) as client:
        resp = client.get("/api/platform/runtime-health")
        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert payload["ok"] is True
        assert payload["model_count"] == 3
        assert payload["chat_model_count"] == 2
        assert payload["embedding_model_count"] == 1

        checks_by_name = {item["name"]: item for item in payload["checks"]}
        assert checks_by_name["chat_probe"]["ok"] is True
        assert "model=gpt-4o status=200" in (
            checks_by_name["chat_probe"]["detail"]
        )
        assert "chat-default:401" in checks_by_name["chat_probe"]["detail"]
        assert checks_by_name["embedding_probe"]["ok"] is True
