from __future__ import annotations

from datetime import UTC, datetime
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, status

from ...team_schemas import (
    TeamCreateRequest,
    TeamInviteRequest,
    TeamMemberRecord,
    TeamRecord,
    TeamRemoveMemberRequest,
    TeamUpdateMemberRoleRequest,
)
from .users import resolve_user_from_auth_header

router = APIRouter()

_TEAMS: dict[str, dict] = {}
_TEAM_MEMBERS: dict[str, dict[str, dict]] = {}


def _ensure_team_exists(team_id: str) -> dict:
    team = _TEAMS.get(team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return team


def _require_manage_permission(team_id: str, user_id: str) -> None:
    member = _TEAM_MEMBERS.get(team_id, {}).get(user_id)
    if not member or member["role"] not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission to manage team")


def team_exists(team_id: str) -> bool:
    return team_id in _TEAMS


def get_team_member_role(team_id: str, user_id: str) -> str | None:
    member = _TEAM_MEMBERS.get(team_id, {}).get(user_id)
    if not member:
        return None
    return str(member.get("role"))


@router.get("/", response_model=List[TeamRecord])
def list_teams(authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    user_id = current["id"]
    result: list[TeamRecord] = []
    for team_id, team in _TEAMS.items():
        if user_id in _TEAM_MEMBERS.get(team_id, {}):
            result.append(TeamRecord(**team))
    return result


@router.post("/", response_model=TeamRecord, status_code=status.HTTP_201_CREATED)
def create_team(payload: TeamCreateRequest, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    now = datetime.now(UTC)
    team_id = f"team_{uuid4().hex[:10]}"
    team = {
        "id": team_id,
        "name": payload.name.strip(),
        "description": payload.description,
        "owner_id": current["id"],
        "created_at": now,
        "updated_at": now,
    }
    _TEAMS[team_id] = team
    _TEAM_MEMBERS.setdefault(team_id, {})[current["id"]] = {
        "team_id": team_id,
        "user_id": current["id"],
        "role": "owner",
        "joined_at": now,
    }
    return TeamRecord(**team)


@router.get("/{team_id}", response_model=TeamRecord)
def get_team(team_id: str, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    _ensure_team_exists(team_id)
    if current["id"] not in _TEAM_MEMBERS.get(team_id, {}):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not in this team")
    return TeamRecord(**_TEAMS[team_id])


@router.get("/{team_id}/members", response_model=List[TeamMemberRecord])
def list_team_members(team_id: str, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    _ensure_team_exists(team_id)
    if current["id"] not in _TEAM_MEMBERS.get(team_id, {}):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not in this team")
    return [TeamMemberRecord(**member) for member in _TEAM_MEMBERS.get(team_id, {}).values()]


@router.post("/{team_id}/invite", response_model=TeamMemberRecord, status_code=status.HTTP_201_CREATED)
def invite_member(
    team_id: str,
    payload: TeamInviteRequest,
    authorization: str | None = Header(default=None),
):
    current = resolve_user_from_auth_header(authorization)
    _ensure_team_exists(team_id)
    _require_manage_permission(team_id, current["id"])

    member = {
        "team_id": team_id,
        "user_id": payload.user_id,
        "role": payload.role,
        "joined_at": datetime.now(UTC),
    }
    _TEAM_MEMBERS.setdefault(team_id, {})[payload.user_id] = member
    _TEAMS[team_id]["updated_at"] = datetime.now(UTC)
    return TeamMemberRecord(**member)


@router.post("/{team_id}/remove", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    team_id: str,
    payload: TeamRemoveMemberRequest,
    authorization: str | None = Header(default=None),
):
    current = resolve_user_from_auth_header(authorization)
    team = _ensure_team_exists(team_id)
    _require_manage_permission(team_id, current["id"])

    if payload.user_id == team["owner_id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove owner")
    if payload.user_id not in _TEAM_MEMBERS.get(team_id, {}):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    _TEAM_MEMBERS[team_id].pop(payload.user_id, None)
    _TEAMS[team_id]["updated_at"] = datetime.now(UTC)
    return None


@router.put("/{team_id}/members/{user_id}/role", response_model=TeamMemberRecord)
def update_member_role(
    team_id: str,
    user_id: str,
    payload: TeamUpdateMemberRoleRequest,
    authorization: str | None = Header(default=None),
):
    current = resolve_user_from_auth_header(authorization)
    _ensure_team_exists(team_id)
    _require_manage_permission(team_id, current["id"])

    member = _TEAM_MEMBERS.get(team_id, {}).get(user_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    member["role"] = payload.role
    _TEAMS[team_id]["updated_at"] = datetime.now(UTC)
    return TeamMemberRecord(**member)
