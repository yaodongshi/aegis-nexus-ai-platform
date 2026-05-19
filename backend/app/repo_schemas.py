from datetime import datetime

from pydantic import BaseModel, Field


class RepoCreateRequest(BaseModel):
    project_id: str
    name: str = Field(min_length=2, max_length=128)
    url: str = ""
    path: str = ""
    default_branch: str = "main"


class RepoRecord(BaseModel):
    id: str
    project_id: str
    name: str
    url: str = ""
    path: str = ""
    current_branch: str = "main"
    sync_status: str = "idle"
    created_at: datetime
    updated_at: datetime


class RepoSwitchBranchRequest(BaseModel):
    branch: str = Field(min_length=1, max_length=128)
