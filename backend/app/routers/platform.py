from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from urllib import error, request

from fastapi import APIRouter, Depends

from ..schemas import (
    PlatformOverviewResponse,
    PlatformRuntimeHealthCheck,
    PlatformRuntimeHealthResponse,
    PlatformServiceStatus,
)
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
    litellm_base = os.getenv("LITELLM_INTERNAL_BASE_URL", "http://litellm:4000").rstrip("/")
    if not master_key:
        return None

    req = request.Request(
        f"{litellm_base}/v1/models",
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


def _call_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict | None = None,
    timeout: int = 5,
) -> tuple[int, dict]:
    body = None
    req_headers = headers.copy() if headers else {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = request.Request(url, headers=req_headers, method=method, data=body)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return int(getattr(resp, "status", 200)), json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            payload_json = json.loads(raw) if raw else {}
        except Exception:
            payload_json = {"detail": raw[:300]}
        return int(exc.code), payload_json


@router.get("/runtime-health", response_model=PlatformRuntimeHealthResponse)
def get_runtime_health() -> PlatformRuntimeHealthResponse:
    litellm_base = os.getenv("LITELLM_INTERNAL_BASE_URL", "http://litellm:4000").rstrip("/")
    master_key = os.getenv("LITELLM_MASTER_KEY", "").strip()
    checks: list[PlatformRuntimeHealthCheck] = []

    if not master_key:
        checks.append(
            PlatformRuntimeHealthCheck(
                name="gateway_auth",
                ok=False,
                blocking=True,
                detail="LITELLM_MASTER_KEY is not configured",
            )
        )
        return PlatformRuntimeHealthResponse(
            ok=False,
            litellm_base=litellm_base,
            checked_at=datetime.now(UTC),
            checks=checks,
        )

    headers = {"Authorization": f"Bearer {master_key}"}
    model_status, model_payload = _call_json(f"{litellm_base}/v1/models", headers=headers)
    models = model_payload.get("data", []) if isinstance(model_payload, dict) else []
    if model_status != 200 or not isinstance(models, list):
        checks.append(
            PlatformRuntimeHealthCheck(
                name="models_list",
                ok=False,
                blocking=True,
                detail=f"HTTP {model_status}",
            )
        )
        return PlatformRuntimeHealthResponse(
            ok=False,
            litellm_base=litellm_base,
            checked_at=datetime.now(UTC),
            checks=checks,
        )

    model_ids = [str(item.get("id", "")) for item in models if isinstance(item, dict)]
    chat_models = [name for name in model_ids if name and "embedding" not in name.lower() and "image" not in name.lower()]
    embedding_models = [name for name in model_ids if "embedding" in name.lower()]

    checks.append(
        PlatformRuntimeHealthCheck(
            name="models_list",
            ok=len(model_ids) > 0,
            blocking=True,
            detail=f"models={len(model_ids)}",
        )
    )

    if chat_models:
        chat_status, chat_payload = _call_json(
            f"{litellm_base}/v1/chat/completions",
            method="POST",
            headers=headers,
            payload={
                "model": chat_models[0],
                "messages": [{"role": "user", "content": "reply ok"}],
                "max_tokens": 8,
                "temperature": 0,
            },
            timeout=15,
        )
        chat_ok = chat_status == 200 and isinstance(chat_payload.get("choices"), list)
        checks.append(
            PlatformRuntimeHealthCheck(
                name="chat_probe",
                ok=chat_ok,
                blocking=True,
                detail=f"model={chat_models[0]} status={chat_status}",
            )
        )
    else:
        checks.append(
            PlatformRuntimeHealthCheck(
                name="chat_probe",
                ok=False,
                blocking=True,
                detail="no chat model in /v1/models",
            )
        )

    if embedding_models:
        emb_status, emb_payload = _call_json(
            f"{litellm_base}/v1/embeddings",
            method="POST",
            headers=headers,
            payload={"model": embedding_models[0], "input": "healthcheck embedding"},
            timeout=15,
        )
        dim = len(((emb_payload.get("data") or [{}])[0].get("embedding") or [])) if isinstance(emb_payload, dict) else 0
        emb_ok = emb_status == 200 and dim > 0
        checks.append(
            PlatformRuntimeHealthCheck(
                name="embedding_probe",
                ok=emb_ok,
                blocking=False,
                detail=f"model={embedding_models[0]} status={emb_status} dim={dim}",
            )
        )
    else:
        checks.append(
            PlatformRuntimeHealthCheck(
                name="embedding_probe",
                ok=True,
                blocking=False,
                detail="no embedding model in /v1/models",
            )
        )

    blocking_failed = [item for item in checks if item.blocking and not item.ok]
    return PlatformRuntimeHealthResponse(
        ok=len(blocking_failed) == 0,
        litellm_base=litellm_base,
        checked_at=datetime.now(UTC),
        model_count=len(model_ids),
        chat_model_count=len(chat_models),
        embedding_model_count=len(embedding_models),
        checks=checks,
    )


@router.get("/overview", response_model=PlatformOverviewResponse)
def get_platform_overview(store: PlatformStore = Depends(get_store)) -> PlatformOverviewResponse:
    providers = store.list_providers()
    keys = store.list_keys()
    skills = store.list_skills()
    sessions = store.list_sessions()
    policies = store.list_policies()
    approvals = store.list_approvals()

    litellm_base = os.getenv("LITELLM_INTERNAL_BASE_URL", "http://litellm:4000").rstrip("/")
    open_webui_base = os.getenv("OPEN_WEBUI_INTERNAL_BASE_URL", "http://open_webui:8080").rstrip("/")
    qdrant_base = os.getenv("QDRANT_INTERNAL_BASE_URL", "http://qdrant:6333").rstrip("/")
    master_key = os.getenv("LITELLM_MASTER_KEY", "").strip()
    gateway_model_count = _count_gateway_models()
    statuses = [
        _probe_service("http://localhost:8000/health"),
        _probe_service(
            f"{litellm_base}/v1/models",
            headers={"Authorization": f"Bearer {master_key}"} if master_key else None,
        ),
        _probe_service(f"{open_webui_base}/health"),
        _probe_service(f"{qdrant_base}/healthz"),
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
        gateway_models_total=gateway_model_count,
        service_status=statuses,
    )
