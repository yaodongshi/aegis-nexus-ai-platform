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

    if x_admin_token and secrets.compare_digest(x_admin_token.strip(), expected_token):
        return

    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.split(" ", 1)[1].strip()
        # Backward compatibility: allow directly passing admin token as Bearer.
        if bearer_token and secrets.compare_digest(bearer_token, expected_token):
            return

        # Integrated frontend uses user login token in Authorization header.
        # Accept a valid signed session token as an alternative to admin token.
        try:
            from ..api.v1.users import resolve_user_from_auth_header

            resolve_user_from_auth_header(authorization)
            return
        except HTTPException:
            pass

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")
