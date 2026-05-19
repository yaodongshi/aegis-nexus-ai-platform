from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, Header, HTTPException, Query, Request, status

from ...knowledge_schemas import KnowledgeCreateRequest, KnowledgeRecord, KnowledgeUpdateRequest
from .projects import get_accessible_project
from .users import resolve_user_from_auth_header

router = APIRouter()


def _get_store(request: Request):
    store = getattr(getattr(request, "app", None), "state", None)
    if store is not None:
        store = getattr(store, "store", None)
    return store


def _resolve_requester(authorization: str | None) -> tuple[str, bool]:
    admin_token = (os.getenv("TEAM_AI_PLATFORM_ADMIN_TOKEN") or "").strip()
    bearer_token = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()

    if admin_token and bearer_token and secrets.compare_digest(bearer_token, admin_token):
        return "admin", True

    current = resolve_user_from_auth_header(authorization)
    return str(current["id"]), False


@router.get("/", response_model=list[KnowledgeRecord])
def list_knowledge(
    request: Request,
    q: str | None = Query(default=None, description="Full-text search"),
    project_id: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
):
    user_id, is_admin = _resolve_requester(authorization)
    store = _get_store(request)

    if store is not None:
        records = store.list_knowledge(project_id=project_id, q=q)
        # 过滤用户有权限的项目
        filtered = []
        for rec in records:
            try:
                if not is_admin:
                    get_accessible_project(rec.project_id, user_id)
                filtered.append(rec)
            except HTTPException:
                continue
        return filtered

    return []


@router.post("/", response_model=KnowledgeRecord, status_code=status.HTTP_201_CREATED)
def create_knowledge(
    request: Request,
    payload: KnowledgeCreateRequest,
    authorization: str | None = Header(default=None),
):
    user_id, is_admin = _resolve_requester(authorization)
    if not is_admin:
        get_accessible_project(payload.project_id, user_id)
    store = _get_store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="Store not available")
    return store.create_knowledge(
        project_id=payload.project_id,
        title=payload.title.strip(),
        content=payload.content,
        fmt=payload.format,
        tags=payload.tags,
        created_by=user_id,
    )


@router.get("/search", response_model=list[KnowledgeRecord])
def search_knowledge(
    request: Request,
    query: str = Query(description="搜索词"),
    limit: int = Query(default=5, ge=1, le=20),
    authorization: str | None = Header(default=None),
):
    _resolve_requester(authorization)
    store = _get_store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="Store not available")
    return store.search_knowledge(query=query, limit=limit)


@router.get("/{doc_id}", response_model=KnowledgeRecord)
def get_knowledge(
    doc_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
):
    user_id, is_admin = _resolve_requester(authorization)
    store = _get_store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="Store not available")
    item = store.get_knowledge(doc_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge doc not found")
    if not is_admin:
        get_accessible_project(item.project_id, user_id)
    return item


@router.put("/{doc_id}", response_model=KnowledgeRecord)
def update_knowledge(
    doc_id: str,
    request: Request,
    payload: KnowledgeUpdateRequest,
    authorization: str | None = Header(default=None),
):
    user_id, is_admin = _resolve_requester(authorization)
    store = _get_store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="Store not available")
    item = store.get_knowledge(doc_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge doc not found")
    if not is_admin:
        get_accessible_project(item.project_id, user_id)
    updates = payload.model_dump(exclude_none=True)
    if "title" in updates and isinstance(updates["title"], str):
        updates["title"] = updates["title"].strip()
    updated = store.update_knowledge(doc_id, updates)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge doc not found")
    return updated


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge(
    doc_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
):
    user_id, is_admin = _resolve_requester(authorization)
    store = _get_store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="Store not available")
    item = store.get_knowledge(doc_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge doc not found")
    if not is_admin:
        get_accessible_project(item.project_id, user_id)
    store.delete_knowledge(doc_id)
    return None
