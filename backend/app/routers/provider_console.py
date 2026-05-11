from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["provider-console"])


@router.get("/provider-console")
def provider_console() -> FileResponse:
    static_root = Path(__file__).resolve().parent.parent / "static"
    return FileResponse(static_root / "provider-console.html")
