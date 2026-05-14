from __future__ import annotations

import json
import os
from urllib import error, request

from fastapi import APIRouter, Depends

from ..schemas import PlatformOverviewResponse, PlatformServiceStatus
from ..store import PlatformStore
from .dependencies import get_store, require_admin_token

router = APIRouter(prefix="/api/platform", tags=["platform"], dependencies=[Depends(require_admin_token)])


def _probe_service(url: str, headers: dict[str, str] | None = None) -> PlatformServiceStatus:
    req = request.Request(url, headers=headers or {}, method="GET")
    try:
        with request.urlopen(req, timeout=2) as resp:
            code = getattr(resp, "status", 200)
            return PlatformServiceStatus(name="", url=url, reachable=200 <= code < 500, detail=f"HTTP {code}")
    except error.HTTPError as exc:
        # 401/403 still proves service is reachable; auth is expected for some endpoints.
        reachable = 200 <= exc.code < 500
        return PlatformServiceStatus(name="", url=url, reachable=reachable, detail=f"HTTP {exc.code}")
    except Exception as exc:  # pragma: no cover
        return PlatformServiceStatus(name="", url=url, reachable=False, detail=str(exc))


def _count_gateway_models() -> int | None:
    master_key = os.getenv("LITELLM_MASTER_KEY", "").strip()
    if not master_key:
        return None

    req = request.Request(
        "http://localhost:4000/v1/models",
        headers={"Authorization": f"Bearer {master_key}"},
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=3) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            models = payload.get("data", [])
            return len(models) if isinstance(models, list) else None
    except Exception:  # pragma: no cover
        return None


@router.get("/overview", response_model=PlatformOverviewResponse)
def get_platform_overview(store: PlatformStore = Depends(get_store)) -> PlatformOverviewResponse:
    providers = store.list_providers()
    keys = store.list_keys()
    skills = store.list_skills()
    sessions = store.list_sessions()
    policies = store.list_policies()
    approvals = store.list_approvals()

    open_webui_port = os.getenv("OPEN_WEBUI_PORT", "9000").strip() or "9000"
    statuses = [
        _probe_service("http://localhost:8000/health"),
        _probe_service("http://localhost:4000/health"),
        _probe_service(f"http://localhost:{open_webui_port}/health"),
        _probe_service("http://localhost:6333/healthz"),
    ]

    statuses[0].name = "backend"
    statuses[1].name = "litellm_gateway"
    statuses[2].name = "open_webui"
    statuses[3].name = "qdrant_infra"

    keys_active = [item for item in keys if item.status == "active"]
    keys_revoked = [item for item in keys if item.status == "revoked"]
    approvals_pending = [item for item in approvals if item.status == "pending"]

    return PlatformOverviewResponse(
        providers_total=len(providers),
        providers_enabled=len([item for item in providers if item.enabled]),
        keys_total=len(keys),
        keys_active=len(keys_active),
        keys_revoked=len(keys_revoked),
        skills_total=len(skills),
        sessions_total=len(sessions),
        policies_total=len(policies),
        approvals_total=len(approvals),
        approvals_pending=len(approvals_pending),
        gateway_models_total=_count_gateway_models(),
        service_status=statuses,
    )
