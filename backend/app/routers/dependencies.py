from __future__ import annotations

from fastapi import Request

from ..store import PlatformStore


def get_store(request: Request) -> PlatformStore:
    return request.app.state.store
