from pydantic import BaseModel

class FeedbackBase(BaseModel):
    content: str
    task_id: int
    user_id: int

class FeedbackCreate(FeedbackBase):
    pass

class FeedbackRead(FeedbackBase):
    id: int
