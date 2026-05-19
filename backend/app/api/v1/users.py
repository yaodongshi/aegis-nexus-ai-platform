from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import UTC, datetime
from typing import List
from uuid import uuid4

import psycopg2
from fastapi import APIRouter, Header, HTTPException, status

from ...user_schemas import (
    UserAdminResetPasswordRequest,
    UserAdminUpdateRequest,
    UserStatusUpdateRequest,
    UserCreate,
    UserLoginRequest,
    UserPublic,
    UserRead,
    UserRegisterRequest,
    UserResetPasswordRequest,
    UserTokenResponse,
)

router = APIRouter()

_USERS: dict[str, dict] = {}
_TOKEN_PREFIX = "tap_"
_DB_SCHEMA_READY = False


def _now_ts() -> int:
    return int(datetime.now(UTC).timestamp())


def _get_auth_secret() -> str:
    return os.getenv("TEAM_AI_PLATFORM_AUTH_SECRET", "team-ai-platform-local-secret")


def _db_dsn() -> str:
    return os.getenv("TEAM_AI_PLATFORM_DB_DSN", "").strip()


def _db_enabled() -> bool:
    return bool(_db_dsn())


def _db_connect():
    return psycopg2.connect(_db_dsn())


def _get_token_ttl_seconds() -> int:
    value = os.getenv("TEAM_AI_PLATFORM_AUTH_TOKEN_TTL_SECONDS", "7200").strip()
    try:
        ttl = int(value)
    except ValueError:
        ttl = 7200
    return max(300, ttl)


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 120000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iterations_raw, salt_hex, digest_hex = encoded.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except Exception:
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return secrets.compare_digest(actual, expected)


def _encode_token(payload: dict) -> str:
    payload_raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_raw).decode("utf-8").rstrip("=")
    signature = hmac.new(_get_auth_secret().encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{_TOKEN_PREFIX}{payload_b64}.{signature}"


def _decode_token(token: str) -> dict:
    if not token.startswith(_TOKEN_PREFIX):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    compact = token[len(_TOKEN_PREFIX):]
    if "." not in compact:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    payload_b64, signature = compact.split(".", 1)
    expected_sig = hmac.new(
        _get_auth_secret().encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    padded = payload_b64 + "=" * ((4 - len(payload_b64) % 4) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
    if int(payload.get("exp", 0)) < _now_ts():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    return payload


def _public_user(user: dict) -> UserPublic:
    return UserPublic(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        role=user["role"],
        is_active=user["is_active"],
    )


def _row_to_user(row: tuple) -> dict:
    return {
        "id": row[0],
        "username": row[1],
        "email": row[2],
        "password_hash": row[3],
        "role": row[4],
        "is_active": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }


def _ensure_user_schema() -> None:
    global _DB_SCHEMA_READY
    if not _db_enabled() or _DB_SCHEMA_READY:
        return

    with _db_connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS backend_auth_users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_backend_auth_users_role_active
            ON backend_auth_users(role, is_active)
            """
        )
    _DB_SCHEMA_READY = True
    _ensure_bootstrap_admin()


def _ensure_bootstrap_admin() -> None:
    disabled = os.getenv("TEAM_AI_PLATFORM_BOOTSTRAP_ADMIN_DISABLED", "false").strip().lower()
    if disabled in {"1", "true", "yes", "on"}:
        return

    admin_username = os.getenv("TEAM_AI_PLATFORM_BOOTSTRAP_ADMIN_USERNAME", "admin").strip() or "admin"
    admin_email = os.getenv("TEAM_AI_PLATFORM_BOOTSTRAP_ADMIN_EMAIL", "admin@local").strip().lower() or "admin@local"
    admin_password = os.getenv("TEAM_AI_PLATFORM_BOOTSTRAP_ADMIN_PASSWORD", "Admin@123456")

    existing = _find_user_by_identity(admin_username) or _find_user_by_identity(admin_email)
    if existing:
        return

    _create_user_record(
        username=admin_username,
        email=admin_email,
        password=admin_password,
        role="admin",
        is_active=True,
    )


def _find_user_by_identity(identity: str) -> dict | None:
    normalized = identity.strip().lower()
    if _db_enabled():
        _ensure_user_schema()
        with _db_connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, username, email, password_hash, role, is_active, created_at, updated_at
                FROM backend_auth_users
                WHERE lower(email) = %s OR lower(username) = %s
                LIMIT 1
                """,
                (normalized, normalized),
            )
            row = cur.fetchone()
            return _row_to_user(row) if row else None

    for user in _USERS.values():
        if user["email"] == normalized or user["username"].lower() == normalized:
            return user
    return None


def _find_user_by_id(user_id: str) -> dict | None:
    if _db_enabled():
        _ensure_user_schema()
        with _db_connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, username, email, password_hash, role, is_active, created_at, updated_at
                FROM backend_auth_users
                WHERE user_id = %s
                LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return _row_to_user(row) if row else None

    return _USERS.get(user_id)


def _list_user_records() -> list[dict]:
    if _db_enabled():
        _ensure_user_schema()
        with _db_connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, username, email, password_hash, role, is_active, created_at, updated_at
                FROM backend_auth_users
                ORDER BY created_at DESC
                """
            )
            return [_row_to_user(row) for row in cur.fetchall()]

    return list(_USERS.values())


def _create_user_record(
    username: str,
    email: str,
    password: str,
    role: str,
    is_active: bool = True,
) -> dict:
    normalized_email = email.strip().lower()
    normalized_username = username.strip()
    normalized_role = role if role in {"admin", "member"} else "member"

    if _find_user_by_identity(normalized_email) or _find_user_by_identity(normalized_username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")

    user_id = f"usr_{uuid4().hex[:12]}"
    password_hash = _hash_password(password)

    if _db_enabled():
        _ensure_user_schema()
        with _db_connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO backend_auth_users (
                    user_id, username, email, password_hash, role, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, normalized_username, normalized_email, password_hash, normalized_role, is_active),
            )
        created = _find_user_by_id(user_id)
        if created is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User creation failed")
        return created

    record = {
        "id": user_id,
        "username": normalized_username,
        "email": normalized_email,
        "password_hash": password_hash,
        "role": normalized_role,
        "is_active": is_active,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    _USERS[user_id] = record
    return record


def _update_user_active(user_id: str, is_active: bool) -> dict | None:
    if _db_enabled():
        _ensure_user_schema()
        with _db_connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE backend_auth_users
                SET is_active = %s, updated_at = now()
                WHERE user_id = %s
                """,
                (is_active, user_id),
            )
            if cur.rowcount == 0:
                return None
        return _find_user_by_id(user_id)

    user = _USERS.get(user_id)
    if user is None:
        return None
    user["is_active"] = is_active
    user["updated_at"] = datetime.now(UTC)
    return user


def _update_user_profile(
    user_id: str,
    username: str | None = None,
    email: str | None = None,
    role: str | None = None,
) -> dict | None:
    current = _find_user_by_id(user_id)
    if current is None:
        return None

    next_username = (username.strip() if username is not None else current["username"])
    next_email = (email.strip().lower() if email is not None else current["email"])
    next_role = role if role is not None else current["role"]
    if next_role not in {"admin", "member"}:
        next_role = "member"

    existing_by_username = _find_user_by_identity(next_username)
    if existing_by_username and existing_by_username["id"] != user_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    existing_by_email = _find_user_by_identity(next_email)
    if existing_by_email and existing_by_email["id"] != user_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    if _db_enabled():
        _ensure_user_schema()
        with _db_connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE backend_auth_users
                SET username = %s,
                    email = %s,
                    role = %s,
                    updated_at = now()
                WHERE user_id = %s
                """,
                (next_username, next_email, next_role, user_id),
            )
            if cur.rowcount == 0:
                return None
        return _find_user_by_id(user_id)

    current["username"] = next_username
    current["email"] = next_email
    current["role"] = next_role
    current["updated_at"] = datetime.now(UTC)
    return current


def _admin_reset_user_password(user_id: str, new_password: str) -> dict | None:
    target = _find_user_by_id(user_id)
    if target is None:
        return None

    password_hash = _hash_password(new_password)
    if _db_enabled():
        _ensure_user_schema()
        with _db_connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE backend_auth_users
                SET password_hash = %s,
                    updated_at = now()
                WHERE user_id = %s
                """,
                (password_hash, user_id),
            )
            if cur.rowcount == 0:
                return None
        return _find_user_by_id(user_id)

    target["password_hash"] = password_hash
    target["updated_at"] = datetime.now(UTC)
    return target


def _require_admin_user(authorization: str | None) -> dict:
    user = _require_bearer(authorization)
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")
    return user


def _require_bearer(authorization: str | None) -> dict:
    if _db_enabled():
        _ensure_user_schema()
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    payload = _decode_token(token)
    user_id = payload.get("sub")
    user = _find_user_by_id(user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    return user


def resolve_user_from_auth_header(authorization: str | None) -> dict:
    return _require_bearer(authorization)

@router.get("/", response_model=List[UserRead])
def list_users():
    # Keep old schema-compatible list endpoint for backward compatibility.
    return []

@router.post("/", response_model=UserRead)
def create_user(user: UserCreate):
    # Keep old schema-compatible create endpoint for backward compatibility.
    return UserRead(id=1, username=user.username, email=user.email, role=user.role, is_active=True)


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegisterRequest):
    username = payload.username.strip()
    email = payload.email.strip().lower()
    if not username or not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid username or email")

    # Self registration is always member. Admin users are managed in admin endpoints.
    record = _create_user_record(
        username=username,
        email=email,
        password=payload.password,
        role="member",
        is_active=True,
    )
    return _public_user(record)


@router.post("/login", response_model=UserTokenResponse)
def login(payload: UserLoginRequest):
    if _db_enabled():
        _ensure_user_schema()

    identity = payload.identity.strip().lower()
    target = _find_user_by_identity(identity)
    if not target or not _verify_password(payload.password, target["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    ttl_seconds = _get_token_ttl_seconds()
    expires_at = _now_ts() + ttl_seconds
    token = _encode_token({"sub": target["id"], "role": target["role"], "exp": expires_at})
    return UserTokenResponse(
        access_token=token,
        expires_in=ttl_seconds,
        user=_public_user(target),
    )


@router.get("/me", response_model=UserPublic)
def me(authorization: str | None = Header(default=None)):
    user = _require_bearer(authorization)
    return _public_user(user)


@router.post("/reset_password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(payload: UserResetPasswordRequest, authorization: str | None = Header(default=None)):
    user = _require_bearer(authorization)
    if not _verify_password(payload.old_password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")

    if _db_enabled():
        _ensure_user_schema()
        with _db_connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE backend_auth_users
                SET password_hash = %s, updated_at = now()
                WHERE user_id = %s
                """,
                (_hash_password(payload.new_password), user["id"]),
            )
    else:
        user["password_hash"] = _hash_password(payload.new_password)
        user["updated_at"] = datetime.now(UTC)

    return None


@router.get("/admin/list", response_model=List[UserPublic])
def list_users_admin(authorization: str | None = Header(default=None)):
    _require_admin_user(authorization)
    return [_public_user(u) for u in _list_user_records()]


@router.post("/admin/create", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user_admin(payload: UserRegisterRequest, authorization: str | None = Header(default=None)):
    _require_admin_user(authorization)
    created = _create_user_record(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        role=payload.role,
        is_active=True,
    )
    return _public_user(created)


@router.patch("/admin/{user_id}/status", response_model=UserPublic)
def update_user_status_admin(
    user_id: str,
    payload: UserStatusUpdateRequest,
    authorization: str | None = Header(default=None),
):
    admin = _require_admin_user(authorization)
    updated = _update_user_active(user_id=user_id, is_active=payload.is_active)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent self-lockout that leaves platform without active admin session.
    if updated["id"] == admin["id"] and not updated["is_active"]:
        _update_user_active(user_id=updated["id"], is_active=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate current admin user",
        )

    return _public_user(updated)


@router.patch("/admin/{user_id}", response_model=UserPublic)
def update_user_admin(
    user_id: str,
    payload: UserAdminUpdateRequest,
    authorization: str | None = Header(default=None),
):
    admin = _require_admin_user(authorization)
    target_before = _find_user_by_id(user_id)
    if target_before is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updated = _update_user_profile(
        user_id=user_id,
        username=payload.username,
        email=payload.email,
        role=payload.role,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target_before["role"] == "admin" and updated["role"] != "admin":
        admins = [u for u in _list_user_records() if u["role"] == "admin" and u.get("is_active", True)]
        if not admins:
            _update_user_profile(user_id=user_id, role="admin")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one active admin is required",
            )

    if updated["id"] == admin["id"] and updated["role"] != "admin":
        _update_user_profile(user_id=user_id, role="admin")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove admin role from current admin user",
        )

    return _public_user(updated)


@router.post("/admin/{user_id}/reset_password", response_model=UserPublic)
def reset_user_password_admin(
    user_id: str,
    payload: UserAdminResetPasswordRequest,
    authorization: str | None = Header(default=None),
):
    _require_admin_user(authorization)
    updated = _admin_reset_user_password(user_id=user_id, new_password=payload.new_password)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _public_user(updated)
