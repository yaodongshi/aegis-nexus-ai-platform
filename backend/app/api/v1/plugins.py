from __future__ import annotations

from datetime import UTC, datetime
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, status

from ...plugin_schemas import ObservabilityLogRecord, PluginCreateRequest, PluginRecord, PluginUpdateRequest
from .teams import get_team_member_role, team_exists
from .users import resolve_user_from_auth_header

router = APIRouter()

_PLUGINS: dict[str, dict] = {}
_OBS_LOGS: list[dict] = []


def _plugin(plugin_id: str) -> dict:
    item = _PLUGINS.get(plugin_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin not found")
    return item


def append_obs_log(team_id: str, resource_type: str, resource_id: str, action: str, detail: str, actor_id: str) -> None:
    """Helper for other modules to append observability log entries."""
    _OBS_LOGS.append({
        "id": f"log_{uuid4().hex[:10]}",
        "team_id": team_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "action": action,
        "detail": detail,
        "actor_id": actor_id,
        "created_at": datetime.now(UTC),
    })


@router.get("/", response_model=List[PluginRecord])
def list_plugins(authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    user_id = current["id"]
    items: list[PluginRecord] = []
    for item in _PLUGINS.values():
        if get_team_member_role(item["team_id"], user_id):
            items.append(PluginRecord(**item))
    return items


@router.post("/", response_model=PluginRecord, status_code=status.HTTP_201_CREATED)
def install_plugin(payload: PluginCreateRequest, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    if not team_exists(payload.team_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    if not get_team_member_role(payload.team_id, current["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not in this team")

    now = datetime.now(UTC)
    plugin_id = f"plg_{uuid4().hex[:10]}"
    record = {
        "id": plugin_id,
        "team_id": payload.team_id,
        "name": payload.name.strip(),
        "description": payload.description,
        "version": payload.version,
        "enabled": True,
        "config": payload.config,
        "installed_by": current["id"],
        "created_at": now,
        "updated_at": now,
    }
    _PLUGINS[plugin_id] = record
    append_obs_log(payload.team_id, "plugin", plugin_id, "installed", f"Plugin {payload.name} installed", current["id"])
    return PluginRecord(**record)


@router.put("/{plugin_id}", response_model=PluginRecord)
def update_plugin(plugin_id: str, payload: PluginUpdateRequest, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    plugin = _plugin(plugin_id)
    if not get_team_member_role(plugin["team_id"], current["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not in this team")

    updates = payload.model_dump(exclude_none=True)
    plugin.update(updates)
    plugin["updated_at"] = datetime.now(UTC)
    return PluginRecord(**plugin)


@router.delete("/{plugin_id}", status_code=status.HTTP_204_NO_CONTENT)
def uninstall_plugin(plugin_id: str, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    plugin = _plugin(plugin_id)
    if not get_team_member_role(plugin["team_id"], current["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not in this team")
    _PLUGINS.pop(plugin_id, None)
    return None


# ── Observability logs ──────────────────────────────────────────────────────

@router.get("/observability/logs", response_model=List[ObservabilityLogRecord])
def list_obs_logs(authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    user_id = current["id"]
    visible_teams = {
        tid for tid in set(item["team_id"] for item in _OBS_LOGS)
        if get_team_member_role(tid, user_id)
    }
    return [ObservabilityLogRecord(**item) for item in _OBS_LOGS if item["team_id"] in visible_teams]
