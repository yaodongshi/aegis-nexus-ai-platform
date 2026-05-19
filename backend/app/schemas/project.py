from pydantic import BaseModel
from typing import Optional

class ProjectBase(BaseModel):
    name: str
    team_id: int

class ProjectCreate(ProjectBase):
    pass

class ProjectRead(ProjectBase):
    id: int
