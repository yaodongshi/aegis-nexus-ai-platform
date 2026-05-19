from datetime import datetime

from pydantic import BaseModel, Field


class TeamCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    description: str = Field(default="", max_length=500)


class TeamRecord(BaseModel):
    id: str
    name: str
    description: str = ""
    owner_id: str
    created_at: datetime
    updated_at: datetime


class TeamMemberRecord(BaseModel):
    team_id: str
    user_id: str
    role: str
    joined_at: datetime


class TeamInviteRequest(BaseModel):
    user_id: str
    role: str = "member"


class TeamRemoveMemberRequest(BaseModel):
    user_id: str


class TeamUpdateMemberRoleRequest(BaseModel):
    role: str
