from __future__ import annotations

from io import BytesIO
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from ..schemas import (
    PageResponse,
    SkillCreateRequest,
    SkillPackExportResponse,
    SkillRecord,
    SkillSearchStatusResponse,
    SkillUpdateRequest,
)
from ..store import PlatformStore
from .dependencies import get_store, require_admin_token

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


@router.get("/search", response_model=PageResponse[SkillRecord])
def search_skills(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    store: PlatformStore = Depends(get_store),
) -> PageResponse[SkillRecord]:
    records = store.search_skills(query=query, limit=limit + offset)
    paged = records[offset : offset + limit]
    return PageResponse[SkillRecord](items=paged, total=len(records), limit=limit, offset=offset)


@router.get("/search-status", response_model=SkillSearchStatusResponse)
def skill_search_status(
    probe: bool = Query(default=False),
    store: PlatformStore = Depends(get_store),
) -> SkillSearchStatusResponse:
    if probe:
        store.probe_skill_embedding()
    return store.get_skill_search_status()


@router.post("", response_model=SkillRecord, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin_token)])
def create_skill(payload: SkillCreateRequest, store: PlatformStore = Depends(get_store)) -> SkillRecord:
    return store.create_skill(payload)


@router.get("/{skill_id}", response_model=SkillRecord)
def get_skill(skill_id: str, store: PlatformStore = Depends(get_store)) -> SkillRecord:
    record = store.get_skill(skill_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return record


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin_token)])
def delete_skill(skill_id: str, store: PlatformStore = Depends(get_store)) -> None:
    deleted = store.delete_skill(skill_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")


@router.patch("/{skill_id}", response_model=SkillRecord,
              dependencies=[Depends(require_admin_token)])
def update_skill(
    skill_id: str,
    payload: SkillUpdateRequest,
    store: PlatformStore = Depends(get_store),
) -> SkillRecord:
    updated = store.update_skill(skill_id, payload)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return updated


@router.get("/{skill_id}/pack/{target}", response_model=SkillPackExportResponse)
def export_skill_pack(
    skill_id: str,
    target: str,
    store: PlatformStore = Depends(get_store),
) -> SkillPackExportResponse:
    try:
        return store.build_skill_pack_export(skill_id=skill_id, target=target)
    except ValueError as exc:
        detail = str(exc)
        if detail == "Skill not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc


@router.get("/{skill_id}/pack-zip/{target}.zip")
def export_skill_pack_zip(
    skill_id: str,
    target: str,
    store: PlatformStore = Depends(get_store),
) -> StreamingResponse:
    try:
        pack = store.build_skill_pack_export(skill_id=skill_id, target=target)
    except ValueError as exc:
        detail = str(exc)
        if detail == "Skill not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for file_item in pack.files:
            zip_file.writestr(file_item.path, file_item.content)
    buffer.seek(0)

    filename = f"skill-pack-{pack.target}-{pack.skill_id}.zip"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)
