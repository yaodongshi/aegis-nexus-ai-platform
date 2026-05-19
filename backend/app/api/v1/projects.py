from __future__ import annotations

from datetime import UTC, datetime
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, status

from ...project_schemas import ProjectCreateRequest, ProjectRecord
from .teams import get_team_member_role, team_exists
from .users import resolve_user_from_auth_header

router = APIRouter()

_PROJECTS: dict[str, dict] = {}


def get_accessible_project(project_id: str, user_id: str) -> dict:
    project = _PROJECTS.get(project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    role = get_team_member_role(project["team_id"], user_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access project")
    return project


@router.get("/", response_model=List[ProjectRecord])
def list_projects(authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    user_id = current["id"]
    items: list[ProjectRecord] = []
    for project in _PROJECTS.values():
        if get_team_member_role(project["team_id"], user_id):
            items.append(ProjectRecord(**project))
    return items


@router.post("/", response_model=ProjectRecord, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreateRequest, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    if not team_exists(payload.team_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    if not get_team_member_role(payload.team_id, current["id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not in this team")

    now = datetime.now(UTC)
    project_id = f"proj_{uuid4().hex[:10]}"
    project = {
        "id": project_id,
        "team_id": payload.team_id,
        "name": payload.name.strip(),
        "description": payload.description,
        "owner_id": current["id"],
        "created_at": now,
        "updated_at": now,
    }
    _PROJECTS[project_id] = project
    return ProjectRecord(**project)


@router.get("/{project_id}", response_model=ProjectRecord)
def get_project(project_id: str, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    project = get_accessible_project(project_id, current["id"])
    return ProjectRecord(**project)
