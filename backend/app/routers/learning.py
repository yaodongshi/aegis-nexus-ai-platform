from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from ..schemas import (
    PageResponse,
    SkillUpdateRecord,
    SkillUpdateSyncRequest,
    TaskRunRecord,
    TaskRunReportRequest,
    TaskRunReportResponse,
)
from ..store import PlatformStore
from .dependencies import get_store, require_admin_token

router = APIRouter(prefix="/api", tags=["learning"])


def require_agent_token(
    x_agent_token: str | None = Header(default=None, alias="X-Agent-Token"),
    authorization: str | None = Header(default=None),
) -> None:
    expected_token = os.getenv("TEAM_AI_PLATFORM_AGENT_TOKEN", "").strip()
    if not expected_token:
        return

    bearer_token = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()
    provided_token = (x_agent_token or bearer_token or "").strip()

    if not provided_token or not secrets.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid agent token")


@router.post("/task-runs/report", response_model=TaskRunReportResponse, status_code=status.HTTP_201_CREATED)
def report_task_run(
    payload: TaskRunReportRequest,
    store: PlatformStore = Depends(get_store),
    _: None = Depends(require_agent_token),
) -> TaskRunReportResponse:
    return store.report_task_run(payload)


@router.get(
    "/task-runs",
    response_model=PageResponse[TaskRunRecord],
    dependencies=[Depends(require_admin_token)],
)
def list_task_runs(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[TaskRunRecord]:
    records = store.list_task_runs()
    paged = records[offset : offset + limit]
    return PageResponse[TaskRunRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.get(
    "/skill-updates",
    response_model=PageResponse[SkillUpdateRecord],
    dependencies=[Depends(require_admin_token)],
)
def list_skill_updates(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[SkillUpdateRecord]:
    records = store.list_skill_updates(status=status_filter)
    paged = records[offset : offset + limit]
    return PageResponse[SkillUpdateRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.post(
    "/skill-updates/{update_id}/apply",
    response_model=SkillUpdateRecord,
    dependencies=[Depends(require_admin_token)],
)
def apply_skill_update(update_id: str, store: PlatformStore = Depends(get_store)) -> SkillUpdateRecord:
    updated = store.apply_skill_update(update_id)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill update not found")
    return updated


@router.post(
    "/skill-updates/{update_id}/sync",
    response_model=SkillUpdateRecord,
    dependencies=[Depends(require_admin_token)],
)
def sync_skill_update(
    update_id: str,
    payload: SkillUpdateSyncRequest,
    store: PlatformStore = Depends(get_store),
) -> SkillUpdateRecord:
    try:
        updated = store.sync_skill_update(update_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill update not found")
    return updated
