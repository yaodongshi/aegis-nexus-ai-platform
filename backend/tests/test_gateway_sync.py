from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend.app.store as store_module
from backend.app.store import PlatformStore


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}: {self.text}")


class _FakeHttpxClient:
    delete_calls: list[str] = []

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self) -> _FakeHttpxClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def get(self, url: str, headers: dict | None = None) -> _FakeResponse:
        assert url.endswith("/model/info")
        return _FakeResponse(
            200,
            {
                "data": [
                    {
                        "model_name": "deprecated-model",
                        "model_info": {"id": "m-del-1", "db_model": True},
                        "litellm_params": {"model": "openai/gpt-4o"},
                    },
                    {
                        "model_name": "deprecated-model",
                        "model_info": {"id": "m-del-2", "db_model": True},
                        "litellm_params": {"model": "openai/gpt-4o"},
                    },
                    {
                        "model_name": "kept-model",
                        "model_info": {"id": "m-keep-1", "db_model": True},
                        "litellm_params": {"model": "openai/gpt-4.1", "api_key": "sk-test"},
                    },
                ]
            },
        )

    def post(self, url: str, headers: dict | None = None, json: dict | None = None) -> _FakeResponse:
        if url.endswith("/model/delete"):
            _FakeHttpxClient.delete_calls.append(str((json or {}).get("id", "")))
            return _FakeResponse(200, {"ok": True})
        if url.endswith("/model/new"):
            return _FakeResponse(200, {"ok": True})
        return _FakeResponse(404, text="not found")


def test_gateway_sync_deletes_all_duplicate_rows_for_removed_model(monkeypatch) -> None:
    store = PlatformStore()

    desired = [
        {
            "model_name": "kept-model",
            "litellm_params": {"model": "openai/gpt-4.1", "api_key": "sk-test"},
        }
    ]

    monkeypatch.setattr(
        store,
        "_build_litellm_runtime_artifacts",
        lambda: ({"model_list": desired}, {}, 0, "none"),
    )
    monkeypatch.setattr(store, "_litellm_base_url", lambda: "http://litellm.test")
    monkeypatch.setattr(store, "_litellm_master_key", lambda: "master-key")
    monkeypatch.setattr(store_module.httpx, "Client", _FakeHttpxClient)
    _FakeHttpxClient.delete_calls = []

    result = store.sync_litellm_gateway_runtime()

    assert result.ok is True
    assert sorted(_FakeHttpxClient.delete_calls) == ["m-del-1", "m-del-2"]
