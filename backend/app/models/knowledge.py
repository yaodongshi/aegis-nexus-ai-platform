from sqlmodel import SQLModel, Field
from typing import Optional

class Knowledge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    project_id: int = Field(foreign_key="project.id")
