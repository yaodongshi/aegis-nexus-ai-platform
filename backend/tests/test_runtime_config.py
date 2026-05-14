from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app


def test_runtime_config_preview_and_apply(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/providers",
            json={
                "name": "OpenAI Prod",
                "provider_type": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "sk-test-openai-123456",
                "preset_key": "openai_official",
                "scope": "unified",
                "apps": ["open_webui", "codex"],
                "api_format": "openai",
                "enabled": True,
                "metadata": {"model_ids": ["gpt-4.1", "gpt-5"]},
            },
        )
        assert create_resp.status_code == 201, create_resp.text

        preview_resp = client.get("/api/v1/runtime/litellm-config")
        assert preview_resp.status_code == 200, preview_resp.text
        preview = preview_resp.json()
        assert preview["provider_count"] == 1
        assert preview["model_count"] == 2

        model_names = [entry["model_name"] for entry in preview["config"]["model_list"]]
        assert model_names == sorted(model_names)
        assert "openai_official-gpt-4-1" in model_names
        assert "openai_official-gpt-5" in model_names

        apply_resp = client.post(
            "/api/v1/runtime/litellm-config/apply",
            json={"output_dir": str(tmp_path)},
        )
        assert apply_resp.status_code == 200, apply_resp.text
        apply_payload = apply_resp.json()

        config_path = Path(apply_payload["config_path"])
        env_path = Path(apply_payload["env_path"])
        assert config_path.exists()
        assert env_path.exists()

        config_content = config_path.read_text(encoding="utf-8")
        env_content = env_path.read_text(encoding="utf-8")
        assert "openai_official-gpt-5" in config_content
        assert "TEAM_AI_LITELLM_PROVIDER_" in env_content


def test_runtime_config_respects_enabled_flag(monkeypatch) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)

    with TestClient(app) as client:
        disabled_resp = client.post(
            "/api/providers",
            json={
                "name": "Disabled Provider",
                "provider_type": "openai",
                "base_url": "https://api.openai.com",
                "api_key": "sk-disabled-123456",
                "scope": "unified",
                "apps": ["open_webui"],
                "api_format": "openai",
                "enabled": False,
            },
        )
        assert disabled_resp.status_code == 201, disabled_resp.text

        preview_resp = client.get("/api/v1/runtime/litellm-config")
        assert preview_resp.status_code == 200, preview_resp.text
        preview = preview_resp.json()
        assert preview["provider_count"] == 0
        assert preview["model_count"] == 0


def test_runtime_config_langfuse_profile(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)
    monkeypatch.setenv("TEAM_AI_PLATFORM_OBSERVABILITY_BACKEND", "langfuse")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-langfuse-demo")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-langfuse-demo")
    monkeypatch.setenv("LANGFUSE_HOST", "https://langfuse.example.com")

    with TestClient(app) as client:
        preview_resp = client.get("/api/v1/runtime/litellm-config")
        assert preview_resp.status_code == 200, preview_resp.text
        preview = preview_resp.json()
        assert preview["observability_backend"] == "langfuse"
        assert preview["config"]["litellm_settings"]["success_callback"] == ["langfuse"]

        apply_resp = client.post(
            "/api/v1/runtime/litellm-config/apply",
            json={"output_dir": str(tmp_path)},
        )
        assert apply_resp.status_code == 200, apply_resp.text
        apply_payload = apply_resp.json()
        assert apply_payload["observability_backend"] == "langfuse"

        env_content = Path(apply_payload["env_path"]).read_text(encoding="utf-8")
        assert "LANGFUSE_PUBLIC_KEY=pk-langfuse-demo" in env_content
        assert "LANGFUSE_SECRET_KEY=sk-langfuse-demo" in env_content
        assert "LANGFUSE_HOST=https://langfuse.example.com" in env_content


def test_runtime_config_helicone_profile(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("TEAM_AI_PLATFORM_DB_DSN", raising=False)
    monkeypatch.setenv("TEAM_AI_PLATFORM_OBSERVABILITY_BACKEND", "helicone")
    monkeypatch.setenv("HELICONE_API_KEY", "helicone-demo-key")
    monkeypatch.setenv("HELICONE_BASE_URL", "https://helicone.example.com")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    with TestClient(app) as client:
        preview_resp = client.get("/api/v1/runtime/litellm-config")
        assert preview_resp.status_code == 200, preview_resp.text
        preview = preview_resp.json()
        assert preview["observability_backend"] == "helicone"
        assert preview["config"]["litellm_settings"]["success_callback"] == ["helicone"]

        apply_resp = client.post(
            "/api/v1/runtime/litellm-config/apply",
            json={"output_dir": str(tmp_path)},
        )
        assert apply_resp.status_code == 200, apply_resp.text
        apply_payload = apply_resp.json()
        assert apply_payload["observability_backend"] == "helicone"

        env_content = Path(apply_payload["env_path"]).read_text(encoding="utf-8")
        assert "HELICONE_API_KEY=helicone-demo-key" in env_content
        assert "HELICONE_BASE_URL=https://helicone.example.com" in env_content
