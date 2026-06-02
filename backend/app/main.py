from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import Response


from .core.config import get_settings
from .harness.trace_bridge import ensure_trace_id
from .routers import (
    approvals,
    control_plane_v2,
    harness,
    health,
    keys,
    learning,
    models,
    openai_compat,
    platform,
    policies,
    provider_console,
    providers,
    runtime_config,
    sessions,
    skills,
)
from .harness import HarnessPlanLockStore, RuntimeAdapterRegistry
from .store import PlatformStore
from .api.v1 import (
    agents_router,
    auditlogs_router,
    feedbacks_router,
    knowledge_rag_router,
    knowledge_router,
    plugins_router,
    projects_router,
    repos_router,
    settings_router,
    tasks_router,
    teams_router,
    users_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = PlatformStore()
    app.state.store.seed_defaults()
    app.state.harness_store = HarnessPlanLockStore()
    app.state.runtime_registry = RuntimeAdapterRegistry()
    yield


settings = get_settings()
app = FastAPI(title=settings.project_name, lifespan=lifespan)

COMPAT_API_PREFIXES = (
    "/api/v1/teams",
    "/api/v1/projects",
    "/api/v1/tasks",
    "/api/v1/plugins",
)


@app.middleware("http")
async def add_compat_deprecation_headers(request: Request, call_next):
    incoming_trace_id = request.headers.get("X-Trace-Id")
    if not incoming_trace_id and request.url.path.startswith(
        "/api/v1/harness/traces/"
    ):
        incoming_trace_id = request.url.path.rsplit("/", 1)[-1]
    ensure_trace_id(request, incoming_trace_id)
    response: Response = await call_next(request)
    trace_id = getattr(request.state, "trace_id", "")
    if trace_id:
        response.headers["X-Trace-Id"] = trace_id
    path = request.url.path
    if any(path.startswith(prefix) for prefix in COMPAT_API_PREFIXES):
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "Fri, 31 Jul 2026 23:59:59 GMT"
        response.headers["X-Compat-Module"] = "legacy-business-module"
        response.headers["Link"] = (
            '</docs/API_AND_FEATURE_CLEANUP_MATRIX.md>; rel="deprecation"'
        )
    return response


app.include_router(health.router)
app.include_router(
    openai_compat.router
)  # Responses API → Chat Completions shim
app.include_router(provider_console.router)
app.include_router(platform.router)
app.include_router(models.router)
app.include_router(keys.router)
app.include_router(providers.public_router)
app.include_router(providers.router)
app.include_router(skills.router)
app.include_router(learning.router)
app.include_router(runtime_config.router)
app.include_router(sessions.router)
app.include_router(policies.router)
app.include_router(approvals.router)
app.include_router(control_plane_v2.router)
app.include_router(harness.router)

# 新增主线业务API
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])
app.include_router(teams_router, prefix="/api/v1/teams", tags=["teams"])
app.include_router(
    projects_router, prefix="/api/v1/projects", tags=["projects"]
)
app.include_router(repos_router, prefix="/api/v1/repos", tags=["repos"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(tasks_router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(
    knowledge_router, prefix="/api/v1/knowledge", tags=["knowledge"]
)
app.include_router(
    knowledge_rag_router,
    prefix="/api/v1/knowledge",
    tags=["knowledge-rag"],
)
app.include_router(plugins_router, prefix="/api/v1/plugins", tags=["plugins"])
app.include_router(
    feedbacks_router, prefix="/api/v1/feedbacks", tags=["feedbacks"]
)
app.include_router(
    auditlogs_router, prefix="/api/v1/auditlogs", tags=["auditlogs"]
)
app.include_router(
    settings_router, prefix="/api/v1/settings", tags=["settings"]
)
