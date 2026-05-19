from __future__ import annotations

from datetime import UTC, datetime
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, status

from ...agent_schemas import AgentCreateRequest, AgentRecord, AgentUpdateRequest
from .projects import get_accessible_project
from .users import resolve_user_from_auth_header

router = APIRouter()

_AGENTS: dict[str, dict] = {}


def _get_agent(agent_id: str) -> dict:
    record = _AGENTS.get(agent_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return record


@router.get("/", response_model=List[AgentRecord])
def list_agents(authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    user_id = current["id"]
    items: list[AgentRecord] = []
    for item in _AGENTS.values():
        try:
            get_accessible_project(item["project_id"], user_id)
            items.append(AgentRecord(**item))
        except HTTPException:
            continue
    return items


@router.post("/", response_model=AgentRecord, status_code=status.HTTP_201_CREATED)
def create_agent(payload: AgentCreateRequest, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    get_accessible_project(payload.project_id, current["id"])

    now = datetime.now(UTC)
    agent_id = f"agt_{uuid4().hex[:10]}"
    record = {
        "id": agent_id,
        "project_id": payload.project_id,
        "name": payload.name.strip(),
        "description": payload.description,
        "system_prompt": payload.system_prompt,
        "status": "active",
        "tags": payload.tags,
        "version": 1,
        "created_by": current["id"],
        "created_at": now,
        "updated_at": now,
    }
    _AGENTS[agent_id] = record
    return AgentRecord(**record)


@router.get("/{agent_id}", response_model=AgentRecord)
def get_agent(agent_id: str, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    agent = _get_agent(agent_id)
    get_accessible_project(agent["project_id"], current["id"])
    return AgentRecord(**agent)


@router.put("/{agent_id}", response_model=AgentRecord)
def update_agent(
    agent_id: str,
    payload: AgentUpdateRequest,
    authorization: str | None = Header(default=None),
):
    current = resolve_user_from_auth_header(authorization)
    agent = _get_agent(agent_id)
    get_accessible_project(agent["project_id"], current["id"])

    updates = payload.model_dump(exclude_none=True)
    if "name" in updates and isinstance(updates["name"], str):
        updates["name"] = updates["name"].strip()

    if updates:
        if any(k in updates for k in ("name", "description", "system_prompt", "tags")):
            agent["version"] += 1
        agent.update(updates)
        agent["updated_at"] = datetime.now(UTC)
    return AgentRecord(**agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: str, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    agent = _get_agent(agent_id)
    get_accessible_project(agent["project_id"], current["id"])
    _AGENTS.pop(agent_id, None)
    return None
