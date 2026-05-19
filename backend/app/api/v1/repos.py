from __future__ import annotations

from datetime import UTC, datetime
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, status

from ...repo_schemas import RepoCreateRequest, RepoRecord, RepoSwitchBranchRequest
from .projects import get_accessible_project
from .users import resolve_user_from_auth_header

router = APIRouter()

_REPOS: dict[str, dict] = {}


def _get_repo(repo_id: str) -> dict:
    repo = _REPOS.get(repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repo not found")
    return repo


@router.get("/", response_model=List[RepoRecord])
def list_repos(authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    user_id = current["id"]
    items: list[RepoRecord] = []
    for repo in _REPOS.values():
        try:
            get_accessible_project(repo["project_id"], user_id)
            items.append(RepoRecord(**repo))
        except HTTPException:
            continue
    return items


@router.post("/", response_model=RepoRecord, status_code=status.HTTP_201_CREATED)
def create_repo(payload: RepoCreateRequest, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    get_accessible_project(payload.project_id, current["id"])

    now = datetime.now(UTC)
    repo_id = f"repo_{uuid4().hex[:10]}"
    repo = {
        "id": repo_id,
        "project_id": payload.project_id,
        "name": payload.name.strip(),
        "url": payload.url,
        "path": payload.path,
        "current_branch": payload.default_branch,
        "sync_status": "idle",
        "created_at": now,
        "updated_at": now,
    }
    _REPOS[repo_id] = repo
    return RepoRecord(**repo)


@router.get("/{repo_id}", response_model=RepoRecord)
def get_repo(repo_id: str, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    repo = _get_repo(repo_id)
    get_accessible_project(repo["project_id"], current["id"])
    return RepoRecord(**repo)


@router.post("/{repo_id}/switch-branch", response_model=RepoRecord)
def switch_branch(
    repo_id: str,
    payload: RepoSwitchBranchRequest,
    authorization: str | None = Header(default=None),
):
    current = resolve_user_from_auth_header(authorization)
    repo = _get_repo(repo_id)
    get_accessible_project(repo["project_id"], current["id"])

    repo["current_branch"] = payload.branch
    repo["updated_at"] = datetime.now(UTC)
    return RepoRecord(**repo)


@router.post("/{repo_id}/sync", response_model=RepoRecord)
def sync_repo(repo_id: str, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    repo = _get_repo(repo_id)
    get_accessible_project(repo["project_id"], current["id"])

    repo["sync_status"] = "synced"
    repo["updated_at"] = datetime.now(UTC)
    return RepoRecord(**repo)
