from datetime import datetime

from pydantic import BaseModel, Field


class PluginCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    description: str = ""
    version: str = "1.0.0"
    config: dict = Field(default_factory=dict)
    team_id: str


class PluginUpdateRequest(BaseModel):
    config: dict | None = None
    enabled: bool | None = None


class PluginRecord(BaseModel):
    id: str
    team_id: str
    name: str
    description: str = ""
    version: str
    enabled: bool = True
    config: dict = Field(default_factory=dict)
    installed_by: str
    created_at: datetime
    updated_at: datetime


class ObservabilityLogRecord(BaseModel):
    id: str
    team_id: str
    resource_type: str
    resource_id: str
    action: str
    detail: str
    actor_id: str
    created_at: datetime
