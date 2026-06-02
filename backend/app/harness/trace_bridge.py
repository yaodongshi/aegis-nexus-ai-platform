from __future__ import annotations

from fastapi import Header

from .schemas import new_trace_id


def resolve_trace_id(
    x_trace_id: str | None = Header(default=None, alias="X-Trace-Id"),
) -> str:
    trace_id = (x_trace_id or "").strip()
    if trace_id:
        return trace_id
    return new_trace_id()
