from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    resource_type: str  # task | agent | project | knowledge
    resource_id: str
    content: str = Field(min_length=1, max_length=2000)
    rating: int | None = Field(default=None, ge=1, le=5)


class FeedbackRecord(BaseModel):
    id: str
    resource_type: str
    resource_id: str
    content: str
    rating: int | None = None
    created_by: str
    created_at: datetime


class AuditLogRecord(BaseModel):
    id: str
    actor_id: str
    actor_name: str
    action: str          # create | update | delete | login | invite | etc.
    resource_type: str
    resource_id: str
    detail: str
    created_at: datetime
