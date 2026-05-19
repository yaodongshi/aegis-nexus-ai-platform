from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
from backend.app.routers import openai_compat


def test_skill_search_lexical_fallback(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        first = client.post(
            "/api/skills",
            json={
                "name": "代码审查助手",
                "description": "关注安全、性能和可读性",
                "system_prompt": "你是专业代码审查助手",
                "category": "code",
                "tags": ["review", "python"],
            },
        )
        assert first.status_code == 201, first.text

        second = client.post(
            "/api/skills",
            json={
                "name": "销售分析助手",
                "description": "聚焦业绩分析",
                "system_prompt": "你是销售分析助手",
                "category": "business",
                "tags": ["sales"],
            },
        )
        assert second.status_code == 201, second.text

        search_resp = client.get("/api/skills/search", params={"query": "代码审查", "limit": 5})
        assert search_resp.status_code == 200, search_resp.text
        payload = search_resp.json()
        assert payload["total"] >= 1
        assert payload["items"][0]["name"] == "代码审查助手"


class _FakeAsyncResponse:
    status_code = 200
    text = "ok"

    def __init__(self, payload: dict):
        self._payload = payload

    def json(self) -> dict:
        return {
            "choices": [
                {
                    "message": {
                        "content": "stubbed",
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
            "_request_payload": self._payload,
        }


class _FakeAsyncClient:
    last_payload: dict | None = None

    def __init__(self, *args, **kwargs):  # noqa: D401, ANN002, ANN003
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: ANN001
        return False

    async def post(self, url: str, json: dict, headers: dict):  # noqa: A002
        _FakeAsyncClient.last_payload = json
        return _FakeAsyncResponse(json)


def test_responses_supports_skill_prompt_injection(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)
    monkeypatch.setattr(openai_compat.httpx, "AsyncClient", _FakeAsyncClient)

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/skills",
            json={
                "name": "代码审查助手",
                "description": "专业代码审查",
                "system_prompt": "你是严格的代码审查助手",
                "category": "code",
                "tags": ["review"],
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        skill_id = create_resp.json()["id"]

        response = client.post(
            "/v1/responses",
            json={
                "model": "qwen-max",
                "input": "请检查这段代码",
                "skill_id": skill_id,
            },
            headers={"Authorization": "Bearer test-key"},
        )
        assert response.status_code == 200, response.text

        payload = _FakeAsyncClient.last_payload
        assert payload is not None
        assert payload["messages"][0]["role"] == "system"
        assert "代码审查助手" in payload["messages"][0]["content"]


def test_responses_skill_not_found(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        response = client.post(
            "/v1/responses",
            json={
                "model": "qwen-max",
                "input": "hello",
                "skill_id": "skill_not_exist",
            },
            headers={"Authorization": "Bearer test-key"},
        )
        assert response.status_code == 404


def test_skill_search_status_endpoint(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        response = client.get("/api/skills/search-status")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["mode"] in {"vector", "lexical", "warming"}
        assert isinstance(payload["qdrant_enabled"], bool)
        assert payload["embedding_model"] == "text-embedding-v3"
        assert "last_search_mode" in payload
        assert "last_search_latency_ms" in payload
        assert "last_search_result_count" in payload
