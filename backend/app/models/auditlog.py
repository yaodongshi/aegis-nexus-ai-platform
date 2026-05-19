from sqlmodel import SQLModel, Field
from typing import Optional

class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    action: str
    user_id: int = Field(foreign_key="user.id")
    detail: str
