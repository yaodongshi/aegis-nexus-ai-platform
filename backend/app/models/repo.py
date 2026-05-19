from sqlmodel import SQLModel, Field
from typing import Optional

class Repo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    url: str
    project_id: int = Field(foreign_key="project.id")
