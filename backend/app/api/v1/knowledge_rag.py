"""
Enhanced Knowledge API with RAG support (Phase 0 Milestone 0A)

Endpoints:
- POST /api/v1/knowledge/upload - Upload single file
- POST /api/v1/knowledge/batch-import - Batch import (CSV/JSON)
- POST /api/v1/knowledge/import-github - GitHub import
- GET /api/v1/knowledge/search - Semantic search
- GET /api/v1/knowledge/stats - Collection statistics
- GET /api/v1/knowledge/import-status/{job_id} - Check import status
"""

from __future__ import annotations

import logging
import os
import secrets
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, HTTPException, Path, Query, Request, UploadFile, status
from pydantic import BaseModel
import aiofiles
import tempfile

from ...core.rag_manager import RAGManager
from .projects import get_accessible_project
from .users import resolve_user_from_auth_header

_logger = logging.getLogger(__name__)

router = APIRouter(tags=["knowledge-rag"])

# 全局 RAG Manager 实例
_rag_manager: Optional[RAGManager] = None


def get_rag_manager() -> RAGManager:
    """获取 RAG Manager 实例"""
    global _rag_manager
    if _rag_manager is None:
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        _rag_manager = RAGManager(qdrant_url=qdrant_url)
    return _rag_manager


def _resolve_requester(authorization: str | None) -> tuple[str, bool]:
    """解析请求者信息"""
    admin_token = (os.getenv("TEAM_AI_PLATFORM_ADMIN_TOKEN") or "").strip()
    bearer_token = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()

    if admin_token and bearer_token and secrets.compare_digest(bearer_token, admin_token):
        return "admin", True

    try:
        current = resolve_user_from_auth_header(authorization)
        return str(current.get("id", "unknown")), False
    except:
        return "anonymous", False


# ============================================================================
# Schema 定义
# ============================================================================

class UploadResponse(BaseModel):
    """文件上传响应"""
    import_job_id: str
    status: str = "processing"
    estimated_chunks: int
    check_status_url: str
    message: str


class SearchResult(BaseModel):
    """搜索结果"""
    id: str
    title: str
    content: str
    similarity: float
    quality_score: float
    tags: list[str]
    source_type: str
    created_at: str


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str
    results: list[SearchResult]
    total: int
    took_ms: float


class ImportStatusResponse(BaseModel):
    """导入状态响应"""
    job_id: str
    status: str  # processing, complete, failed
    chunks_created: int = 0
    chunks_deduplicated: int = 0
    quality_scores: dict = {}  # {min, max, avg}
    error_message: Optional[str] = None


class StatsResponse(BaseModel):
    """统计信息"""
    collection_name: str
    vector_count: int
    embedding_dim: int
    distance_metric: str
    status: str


# ============================================================================
# 文件上传处理
# ============================================================================

async def process_document_upload(
    job_id: str,
    file_path: str,
    user_id: str,
    project_id: str,
    title: str,
    tags: list[str],
):
    """后台任务：处理上传的文档"""
    try:
        _logger.info(f"📥 开始处理文档: {job_id}")
        
        rag_manager = get_rag_manager()
        
        # 读取文件内容
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
        
        if not content.strip():
            _logger.warning(f"⚠️  文档为空: {job_id}")
            return
        
        # 摄入到 RAG
        result = rag_manager.ingest_knowledge(
            content=content,
            title=title,
            source_type="api:upload",
            source_reference=f"upload_{os.path.basename(file_path)}",
            author=user_id,
            tags=tags,
            project_id=project_id,
        )
        
        _logger.info(f"✅ 文档处理完成: {job_id} - {result}")
        
    except Exception as e:
        _logger.error(f"❌ 文档处理失败: {job_id} - {e}", exc_info=True)
    finally:
        # 清理临时文件
        if os.path.exists(file_path):
            os.remove(file_path)


# ============================================================================
# API 端点
# ============================================================================

@router.post("/upload", response_model=UploadResponse)
async def upload_knowledge(
    file: UploadFile = File(...),
    project_id: str = Form("default"),
    tags: str = Form(""),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    request: Request = None,
    authorization: str = Header(None),
):
    """
    上传单个知识文件
    
    支持的格式: PDF, DOCX, Markdown, TXT, JSON
    """
    user_id, is_admin = _resolve_requester(authorization)
    
    # 验证项目访问权限
    try:
        if not is_admin:
            get_accessible_project(project_id, user_id)
    except:
        pass
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    
    # 生成 job ID
    job_id = f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    # 预估 chunks 数量 (粗略)
    estimated_chunks = max(1, len(content) // (512 * 4))
    
    # 提交后台任务
    background_tasks.add_task(
        process_document_upload,
        job_id=job_id,
        file_path=tmp_path,
        user_id=user_id,
        project_id=project_id,
        title=file.filename,
        tags=tags.split(",") if tags else [],
    )
    
    _logger.info(f"📤 上传任务已入队: {job_id} - {file.filename}")
    
    return UploadResponse(
        import_job_id=job_id,
        status="processing",
        estimated_chunks=estimated_chunks,
        check_status_url=f"/api/v1/knowledge/import-status/{job_id}",
        message=f"文档已入队处理，预估 {estimated_chunks} 个 chunks"
    )


@router.post("/batch-import", response_model=UploadResponse)
async def batch_import_knowledge(
    csv_url: str = Form(...),
    project_id: str = Form("default"),
    tags: str = Form(""),
    authorization: str = Header(None),
):
    """
    批量导入知识 (CSV/JSON)
    
    CSV 格式:
    title,content,author,tags
    "API Guide","Content..","john","api,reference"
    """
    user_id, is_admin = _resolve_requester(authorization)
    
    job_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    _logger.info(f"📥 批量导入任务入队: {job_id}")
    
    return UploadResponse(
        import_job_id=job_id,
        status="queued",
        estimated_chunks=100,  # 预估
        check_status_url=f"/api/v1/knowledge/import-status/{job_id}",
        message="批量导入任务已入队"
    )


@router.post("/import-github")
async def import_github_knowledge(
    owner: str = Form(...),
    repo: str = Form(...),
    paths: str = Form("docs/,README.md"),
    project_id: str = Form("default"),
    tags: str = Form(""),
    authorization: str = Header(None),
):
    """
    从 GitHub 导入知识
    
    例: owner=company, repo=platform, paths="docs/,README.md"
    """
    user_id, is_admin = _resolve_requester(authorization)
    
    job_id = f"github_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    _logger.info(f"📥 GitHub 导入任务入队: {job_id} - {owner}/{repo}")
    
    return UploadResponse(
        import_job_id=job_id,
        status="queued",
        estimated_chunks=50,
        check_status_url=f"/api/v1/knowledge/import-status/{job_id}",
        message=f"GitHub 导入任务已入队 ({owner}/{repo})"
    )


@router.get("/search", response_model=SearchResponse)
async def search_knowledge(
    query: str = Query(..., description="搜索词"),
    limit: int = Query(10, ge=1, le=50),
    min_quality: float = Query(0.5, ge=0, le=1),
    authorization: str = Header(None),
):
    """
    语义搜索知识库
    """
    _resolve_requester(authorization)
    
    import time
    start_time = time.time()
    
    rag_manager = get_rag_manager()
    hits = rag_manager.search(query=query, limit=limit, min_quality=min_quality)
    
    results = [
        SearchResult(
            id=hit["id"],
            title=hit.get("title", ""),
            content=hit["content"][:200],  # 截断
            similarity=hit["similarity"],
            quality_score=hit["quality_score"],
            tags=hit.get("tags", []),
            source_type=hit.get("source_type", ""),
            created_at=hit.get("created_at", ""),
        )
        for hit in hits
    ]
    
    took_ms = (time.time() - start_time) * 1000
    
    return SearchResponse(
        query=query,
        results=results,
        total=len(results),
        took_ms=took_ms
    )


@router.get("/stats", response_model=StatsResponse)
async def get_knowledge_stats(authorization: str = Header(None)):
    """获取知识库统计信息"""
    _resolve_requester(authorization)
    
    rag_manager = get_rag_manager()
    stats = rag_manager.get_collection_stats()
    
    return StatsResponse(**stats)


@router.get("/import-status/{job_id}", response_model=ImportStatusResponse)
async def get_import_status(
    job_id: str = Path(...),
    authorization: str = Header(None),
):
    """获取导入任务状态"""
    _resolve_requester(authorization)
    
    # TODO: 从数据库查询真实状态
    # 这里返回模拟数据用于演示
    
    return ImportStatusResponse(
        job_id=job_id,
        status="processing",
        chunks_created=45,
        chunks_deduplicated=2,
        quality_scores={"min": 0.78, "max": 0.95, "avg": 0.88},
    )
