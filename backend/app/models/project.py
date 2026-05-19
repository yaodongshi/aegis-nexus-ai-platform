from sqlmodel import SQLModel, Field
from typing import Optional

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    team_id: int = Field(foreign_key="team.id")
