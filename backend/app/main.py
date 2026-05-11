from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .core.config import get_settings
from .routers import approvals, health, keys, models, policies, sessions, skills
from .store import PlatformStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = PlatformStore()
    app.state.store.seed_defaults()
    yield


settings = get_settings()
app = FastAPI(title=settings.project_name, lifespan=lifespan)

app.include_router(health.router)
app.include_router(models.router)
app.include_router(keys.router)
app.include_router(skills.router)
app.include_router(sessions.router)
app.include_router(policies.router)
app.include_router(approvals.router)
