from __future__ import annotations

from fastapi import Header
from fastapi import Request

from .schemas import new_trace_id


def ensure_trace_id(
    request: Request,
    incoming_trace_id: str | None = None,
) -> str:
    existing_trace_id = getattr(request.state, "trace_id", "") or ""
    if existing_trace_id.strip():
        return existing_trace_id.strip()

    trace_id = (incoming_trace_id or "").strip() or new_trace_id()
    request.state.trace_id = trace_id
    return trace_id


def resolve_trace_id(
    request: Request,
    x_trace_id: str | None = Header(default=None, alias="X-Trace-Id"),
) -> str:
    return ensure_trace_id(request, x_trace_id)
