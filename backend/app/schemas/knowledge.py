from pydantic import BaseModel

class KnowledgeBase(BaseModel):
    title: str
    content: str
    project_id: int

class KnowledgeCreate(KnowledgeBase):
    pass

class KnowledgeRead(KnowledgeBase):
    id: int
