from pydantic import BaseModel
from typing import Optional

class TaskBase(BaseModel):
    title: str
    project_id: int
    assignee_id: Optional[int] = None

class TaskCreate(TaskBase):
    pass

class TaskRead(TaskBase):
    id: int
