from datetime import datetime

from pydantic import BaseModel, Field


class AgentCreateRequest(BaseModel):
    project_id: str
    name: str = Field(min_length=2, max_length=128)
    description: str = Field(default="", max_length=800)
    system_prompt: str = ""
    tags: list[str] = Field(default_factory=list)


class AgentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=128)
    description: str | None = Field(default=None, max_length=800)
    system_prompt: str | None = None
    status: str | None = None
    tags: list[str] | None = None


class AgentRecord(BaseModel):
    id: str
    project_id: str
    name: str
    description: str = ""
    system_prompt: str = ""
    status: str = "active"
    tags: list[str] = Field(default_factory=list)
    version: int = 1
    created_by: str
    created_at: datetime
    updated_at: datetime
