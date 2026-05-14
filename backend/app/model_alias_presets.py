# Model Alias Presets for M1
# 模型别名规范实现
# Format: {provider_family}-{capability_tier}-{context_variant}

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelAliasPreset:
    """Model alias preset mapping"""
    alias: str  # Platform-facing alias (e.g., 'gpt4o-pro-128k')
    real_model_id: str  # Real provider model ID (e.g., 'gpt-4o')
    provider: str  # Provider type (e.g., 'openai')
    tier: str  # Capability tier: pro, standard, economy
    context_window: int  # Max context in tokens
    description: str
    supported_capabilities: list[str]  # e.g., ['text', 'vision', 'function_calling']
    cost_per_1m_input_tokens: float  # USD cost
    cost_per_1m_output_tokens: float  # USD cost


# Core model alias presets - 15+ mappings covering production models
ALIAS_PRESETS = [
    # OpenAI: GPT-4 series
    ModelAliasPreset(
        alias="gpt4o-pro-128k",
        real_model_id="gpt-4o",
        provider="openai",
        tier="pro",
        context_window=128000,
        description="GPT-4o - latest flagship model with vision",
        supported_capabilities=["text", "vision", "function_calling", "json_mode"],
        cost_per_1m_input_tokens=5.0,
        cost_per_1m_output_tokens=15.0,
    ),
    ModelAliasPreset(
        alias="gpt4-turbo-128k",
        real_model_id="gpt-4-turbo",
        provider="openai",
        tier="pro",
        context_window=128000,
        description="GPT-4 Turbo with vision (128k context)",
        supported_capabilities=["text", "vision", "function_calling", "json_mode"],
        cost_per_1m_input_tokens=10.0,
        cost_per_1m_output_tokens=30.0,
    ),
    ModelAliasPreset(
        alias="gpt35-turbo-4k",
        real_model_id="gpt-3.5-turbo",
        provider="openai",
        tier="economy",
        context_window=4096,
        description="GPT-3.5 Turbo - fast and affordable",
        supported_capabilities=["text", "function_calling"],
        cost_per_1m_input_tokens=0.5,
        cost_per_1m_output_tokens=1.5,
    ),

    # Anthropic: Claude 3 series
    ModelAliasPreset(
        alias="claude3-opus-200k",
        real_model_id="claude-3-opus-20240229",
        provider="anthropic",
        tier="pro",
        context_window=200000,
        description="Claude 3 Opus - most capable, 200k context",
        supported_capabilities=["text", "vision", "function_calling"],
        cost_per_1m_input_tokens=15.0,
        cost_per_1m_output_tokens=75.0,
    ),
    ModelAliasPreset(
        alias="claude3-sonnet-200k",
        real_model_id="claude-3-sonnet-20240229",
        provider="anthropic",
        tier="standard",
        context_window=200000,
        description="Claude 3 Sonnet - balanced, 200k context",
        supported_capabilities=["text", "vision", "function_calling"],
        cost_per_1m_input_tokens=3.0,
        cost_per_1m_output_tokens=15.0,
    ),
    ModelAliasPreset(
        alias="claude3-haiku-200k",
        real_model_id="claude-3-haiku-20240307",
        provider="anthropic",
        tier="economy",
        context_window=200000,
        description="Claude 3 Haiku - fast and compact, 200k context",
        supported_capabilities=["text", "vision"],
        cost_per_1m_input_tokens=0.8,
        cost_per_1m_output_tokens=4.0,
    ),

    # Google: Gemini series
    ModelAliasPreset(
        alias="gemini-pro-128k",
        real_model_id="gemini-pro",
        provider="google",
        tier="pro",
        context_window=128000,
        description="Gemini Pro - Google's flagship model (128k context)",
        supported_capabilities=["text", "vision", "function_calling"],
        cost_per_1m_input_tokens=1.25,
        cost_per_1m_output_tokens=5.0,
    ),
    ModelAliasPreset(
        alias="gemini-flash-1m",
        real_model_id="gemini-1.5-flash",
        provider="google",
        tier="standard",
        context_window=1000000,
        description="Gemini 1.5 Flash - fast model with 1M context",
        supported_capabilities=["text", "vision", "function_calling"],
        cost_per_1m_input_tokens=0.075,
        cost_per_1m_output_tokens=0.3,
    ),

    # Meta: Llama series (via Together AI or local)
    ModelAliasPreset(
        alias="llama2-70b-4k",
        real_model_id="meta-llama/Llama-2-70b-chat-hf",
        provider="together",
        tier="economy",
        context_window=4096,
        description="Llama 2 70B - open-source flagship",
        supported_capabilities=["text"],
        cost_per_1m_input_tokens=0.9,
        cost_per_1m_output_tokens=1.2,
    ),
    ModelAliasPreset(
        alias="llama3-70b-8k",
        real_model_id="meta-llama/Llama-3-70b-chat-hf",
        provider="together",
        tier="economy",
        context_window=8192,
        description="Llama 3 70B - improved open-source model",
        supported_capabilities=["text", "function_calling"],
        cost_per_1m_input_tokens=0.7,
        cost_per_1m_output_tokens=0.9,
    ),

    # Alibaba: Qwen series (Chinese market)
    ModelAliasPreset(
        alias="qwen-plus-32k",
        real_model_id="qwen-plus",
        provider="alibaba",
        tier="standard",
        context_window=32000,
        description="阿里云通义千问 Plus - 32k context",
        supported_capabilities=["text", "function_calling"],
        cost_per_1m_input_tokens=0.12,
        cost_per_1m_output_tokens=0.18,
    ),
    ModelAliasPreset(
        alias="qwen-turbo-8k",
        real_model_id="qwen-turbo",
        provider="alibaba",
        tier="economy",
        context_window=8192,
        description="阿里云通义千问 Turbo - 8k context",
        supported_capabilities=["text"],
        cost_per_1m_input_tokens=0.03,
        cost_per_1m_output_tokens=0.06,
    ),

    # Local: ollama models (for development/testing)
    ModelAliasPreset(
        alias="mistral-7b-local",
        real_model_id="mistral:7b",
        provider="ollama",
        tier="economy",
        context_window=8192,
        description="Mistral 7B via ollama - local deployment",
        supported_capabilities=["text"],
        cost_per_1m_input_tokens=0.0,
        cost_per_1m_output_tokens=0.0,
    ),
    ModelAliasPreset(
        alias="neural-chat-7b-local",
        real_model_id="neural-chat:7b",
        provider="ollama",
        tier="economy",
        context_window=4096,
        description="Neural Chat 7B via ollama - local deployment",
        supported_capabilities=["text"],
        cost_per_1m_input_tokens=0.0,
        cost_per_1m_output_tokens=0.0,
    ),

    # Azure: OpenAI models
    ModelAliasPreset(
        alias="azure-gpt4-32k",
        real_model_id="gpt-4-32k",
        provider="azure",
        tier="pro",
        context_window=32000,
        description="Azure OpenAI - GPT-4 with 32k context",
        supported_capabilities=["text", "function_calling"],
        cost_per_1m_input_tokens=6.0,
        cost_per_1m_output_tokens=12.0,
    ),
]

# Index structures for quick lookups
_alias_to_preset: dict[str, ModelAliasPreset] = {p.alias: p for p in ALIAS_PRESETS}
_provider_to_presets: dict[str, list[ModelAliasPreset]] = {}
for preset in ALIAS_PRESETS:
    if preset.provider not in _provider_to_presets:
        _provider_to_presets[preset.provider] = []
    _provider_to_presets[preset.provider].append(preset)


def lookup_by_alias(alias: str) -> ModelAliasPreset | None:
    """Look up a preset by its alias (platform name).
    
    Args:
        alias: Platform alias (e.g., 'gpt4o-pro-128k')
        
    Returns:
        ModelAliasPreset or None if not found
    """
    return _alias_to_preset.get(alias)


def lookup_by_real_model_id(model_id: str) -> ModelAliasPreset | None:
    """Look up a preset by its real model ID (provider name).
    
    Args:
        model_id: Real provider model ID (e.g., 'gpt-4o')
        
    Returns:
        ModelAliasPreset or None if not found
    """
    for preset in ALIAS_PRESETS:
        if preset.real_model_id == model_id:
            return preset
    return None


def list_aliases(provider: str | None = None, tier: str | None = None) -> list[ModelAliasPreset]:
    """List all available aliases, optionally filtered.
    
    Args:
        provider: Optional provider filter (e.g., 'openai', 'anthropic')
        tier: Optional tier filter (e.g., 'pro', 'economy')
        
    Returns:
        List of ModelAliasPreset matching filters
    """
    results = ALIAS_PRESETS
    if provider:
        results = [p for p in results if p.provider == provider]
    if tier:
        results = [p for p in results if p.tier == tier]
    return results


def get_providers() -> list[str]:
    """Get list of all available providers."""
    return sorted(list(_provider_to_presets.keys()))


def get_tiers() -> list[str]:
    """Get list of all available tiers."""
    tiers = set()
    for preset in ALIAS_PRESETS:
        tiers.add(preset.tier)
    return sorted(list(tiers))


def validate_alias(alias: str) -> bool:
    """Check if an alias is valid (exists in presets).
    
    Args:
        alias: Alias to validate
        
    Returns:
        True if valid, False otherwise
    """
    return alias in _alias_to_preset


# Export public API
__all__ = [
    'ModelAliasPreset',
    'ALIAS_PRESETS',
    'lookup_by_alias',
    'lookup_by_real_model_id',
    'list_aliases',
    'get_providers',
    'get_tiers',
    'validate_alias',
]
