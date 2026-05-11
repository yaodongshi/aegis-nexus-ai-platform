from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from os import getenv


@dataclass(frozen=True)
class Settings:
    project_name: str = getenv("TEAM_AI_PLATFORM_PROJECT_NAME", "Aegis Nexus AI Platform")
    api_v1_prefix: str = getenv("TEAM_AI_PLATFORM_API_V1_PREFIX", "/api")
    default_admin_email: str = getenv("TEAM_AI_PLATFORM_DEFAULT_ADMIN_EMAIL", "admin@example.com")
    default_model_provider: str = getenv("TEAM_AI_PLATFORM_DEFAULT_MODEL_PROVIDER", "openai")
    default_model_name: str = getenv("TEAM_AI_PLATFORM_DEFAULT_MODEL_NAME", "gpt-4o")


@lru_cache
def get_settings() -> Settings:
    return Settings()
