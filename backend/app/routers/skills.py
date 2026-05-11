from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..schemas import PageResponse, SkillPublishRequest, SkillPublishResponse, SkillRecord
from ..store import PlatformStore
from .dependencies import get_store

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("", response_model=PageResponse[SkillRecord])
def list_skills(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[SkillRecord]:
    records = store.list_skills()
    paged = records[offset : offset + limit]
    return PageResponse[SkillRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.post("/publish", response_model=SkillPublishResponse, status_code=status.HTTP_201_CREATED)
def publish_skill(payload: SkillPublishRequest, store: PlatformStore = Depends(get_store)) -> SkillPublishResponse:
    return store.publish_skill(payload)


@router.get("/{skill_id}", response_model=SkillRecord)
def get_skill(skill_id: str, store: PlatformStore = Depends(get_store)) -> SkillRecord:
    record = store.get_skill(skill_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return record


@router.post("/{skill_id}/rollback", response_model=SkillRecord)
def rollback_skill(skill_id: str, store: PlatformStore = Depends(get_store)) -> SkillRecord:
    record = store.rollback_skill(skill_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return record
