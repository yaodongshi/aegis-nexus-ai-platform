from pydantic import BaseModel

class AgentBase(BaseModel):
    name: str
    project_id: int

class AgentCreate(AgentBase):
    pass

class AgentRead(AgentBase):
    id: int
