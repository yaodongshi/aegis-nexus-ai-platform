from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    project_id: str
    title: str = Field(min_length=2, max_length=256)
    description: str = ""
    assignee_id: str | None = None
    priority: str = "medium"


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=256)
    description: str | None = None
    assignee_id: str | None = None
    priority: str | None = None
    status: str | None = None


class TaskCommentCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class TaskCommentRecord(BaseModel):
    id: str
    task_id: str
    user_id: str
    content: str
    created_at: datetime


class TaskHistoryRecord(BaseModel):
    id: str
    task_id: str
    action: str
    detail: str
    actor_id: str
    created_at: datetime


class TaskRecord(BaseModel):
    id: str
    project_id: str
    title: str
    description: str = ""
    assignee_id: str | None = None
    status: str = "todo"
    priority: str = "medium"
    created_by: str
    created_at: datetime
    updated_at: datetime
