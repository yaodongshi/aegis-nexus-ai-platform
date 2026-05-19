from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    team_id: str
    name: str = Field(min_length=2, max_length=128)
    description: str = Field(default="", max_length=500)


class ProjectRecord(BaseModel):
    id: str
    team_id: str
    name: str
    description: str = ""
    owner_id: str
    created_at: datetime
    updated_at: datetime
