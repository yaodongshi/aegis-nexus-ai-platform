from pydantic import BaseModel
from typing import Optional

class RepoBase(BaseModel):
    name: str
    url: str
    project_id: int

class RepoCreate(RepoBase):
    pass

class RepoRead(RepoBase):
    id: int
