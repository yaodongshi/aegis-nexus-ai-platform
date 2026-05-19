from pydantic import BaseModel

class AuditLogBase(BaseModel):
    action: str
    user_id: int
    detail: str

class AuditLogRead(AuditLogBase):
    id: int
