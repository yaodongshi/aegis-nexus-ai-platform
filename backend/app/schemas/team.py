from pydantic import BaseModel
from typing import Optional

class TeamBase(BaseModel):
    name: str

class TeamCreate(TeamBase):
    pass

class TeamRead(TeamBase):
    id: int
