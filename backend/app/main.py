from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .core.config import get_settings
from .routers import approvals, control_plane_v2, health, keys, learning, models, platform, policies, provider_console, providers, runtime_config, sessions, skills
from .store import PlatformStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = PlatformStore()
    app.state.store.seed_defaults()
    yield


settings = get_settings()
app = FastAPI(title=settings.project_name, lifespan=lifespan)

app.include_router(health.router)
app.include_router(provider_console.router)
app.include_router(platform.router)
app.include_router(models.router)
app.include_router(keys.router)
app.include_router(providers.router)
app.include_router(skills.router)
app.include_router(learning.router)
app.include_router(runtime_config.router)
app.include_router(sessions.router)
app.include_router(policies.router)
app.include_router(approvals.router)
app.include_router(control_plane_v2.router)
