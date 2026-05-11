from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException, Request, status

from ..store import PlatformStore


def get_store(request: Request) -> PlatformStore:
    return request.app.state.store


def require_admin_token(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    authorization: str | None = Header(default=None),
) -> None:
    expected_token = os.getenv("TEAM_AI_PLATFORM_ADMIN_TOKEN", "").strip()
    if not expected_token:
        return

    bearer_token = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()
    provided_token = (x_admin_token or bearer_token or "").strip()

    if not provided_token or not secrets.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")
