from __future__ import annotations

from .schemas import ProviderPresetRecord

PRESET_PROVIDERS: list[ProviderPresetRecord] = [
    ProviderPresetRecord(
        key="openai_official",
        name="OpenAI Official",
        provider_type="openai",
        default_base_url="https://api.openai.com",
        api_format="openai",
        suggested_apps=["codex", "open_webui", "opencode"],
    ),
    ProviderPresetRecord(
        key="anthropic_official",
        name="Anthropic Official",
        provider_type="anthropic",
        default_base_url="https://api.anthropic.com",
        api_format="anthropic",
        suggested_apps=["claude", "opencode"],
    ),
    ProviderPresetRecord(
        key="azure_openai",
        name="Azure OpenAI",
        provider_type="azure_openai",
        default_base_url="https://example.openai.azure.com",
        api_format="openai",
        suggested_apps=["codex", "open_webui"],
    ),
    ProviderPresetRecord(
        key="openrouter",
        name="OpenRouter",
        provider_type="openrouter",
        default_base_url="https://openrouter.ai/api",
        api_format="openai",
        suggested_apps=["claude", "codex", "gemini", "open_webui"],
    ),
    ProviderPresetRecord(
        key="deepseek",
        name="DeepSeek",
        provider_type="deepseek",
        default_base_url="https://api.deepseek.com",
        api_format="openai",
        suggested_apps=["opencode", "openclaw", "open_webui"],
    ),
    ProviderPresetRecord(
        key="custom_openai_compatible",
        name="Custom OpenAI Compatible",
        provider_type="custom",
        default_base_url="https://api.example.com",
        api_format="openai",
        suggested_apps=["claude", "codex", "gemini", "opencode", "openclaw", "open_webui"],
    ),
]
