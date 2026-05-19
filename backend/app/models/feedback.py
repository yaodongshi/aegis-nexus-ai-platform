from sqlmodel import SQLModel, Field
from typing import Optional

class Feedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    task_id: int = Field(foreign_key="task.id")
    user_id: int = Field(foreign_key="user.id")
