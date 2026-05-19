from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeCreateRequest(BaseModel):
    project_id: str
    title: str = Field(min_length=2, max_length=256)
    content: str = Field(min_length=1)
    format: str = "markdown"
    tags: list[str] = Field(default_factory=list)


class KnowledgeUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=256)
    content: str | None = None
    format: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class KnowledgeRecord(BaseModel):
    id: str
    project_id: str
    title: str
    content: str
    format: str = "markdown"
    status: str = "active"
    tags: list[str] = Field(default_factory=list)
    version: int = 1
    created_by: str
    qdrant_chunk_ids: list[str] = Field(default_factory=list)  # Qdrant 向量 chunk ID 列表
    chunk_count: int = 0  # 已向量化的 chunk 数量
    created_at: datetime
    updated_at: datetime
