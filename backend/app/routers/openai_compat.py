"""OpenAI-compatible API layer for the Team AI backend.

This module makes the backend the **single public AI entry-point** for all
clients.  LiteLLM remains the internal AI routing engine; nothing bypasses it.

Architecture
------------
::

    Client (any)
        │
        ▼  POST /v1/responses      ← Responses API shim (OpenCode 1.4.x)
        ▼  POST /v1/chat/completions   ┐
        ▼  GET  /v1/models             ├ transparent proxy → litellm:4000
        ▼  ANY  /v1/*                  ┘
    Backend :8000
        │
        ▼  always /v1/chat/completions
    LiteLLM :4000  (internal microservice, not exposed to clients)
        │
        ▼
    DeepSeek / any provider

Why
---
* LiteLLM's ``/v1/responses`` endpoint calls ``{api_base}/responses`` on the
  upstream, which does not exist on OpenAI-compatible backends (DeepSeek etc.).
* Having the backend as the single entry-point gives us a consistent place for
  auth enforcement, audit logging, and future policy controls – independent of
  which AI client is used (OpenWebUI, OpenCode, curl, …).
* LiteLLM still does all the heavy lifting: model routing, rate limiting, cost
  tracking, provider fallbacks, observability.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# Internal LiteLLM base URL
# ---------------------------------------------------------------------------
# Inside Docker Compose the LiteLLM service is reachable via its service name.
# Override with LITELLM_INTERNAL_BASE_URL for non-Docker / dev environments.
_LITELLM_INTERNAL_BASE = os.getenv(
    "LITELLM_INTERNAL_BASE_URL",
    "http://litellm:4000",
).rstrip("/")


# ---------------------------------------------------------------------------
# Responses API helpers
# ---------------------------------------------------------------------------

def _input_to_messages(
    input_: Any,
    instructions: str | None,
) -> list[dict[str, Any]]:
    """Convert a Responses API ``input`` field into a ``messages`` array."""
    messages: list[dict[str, Any]] = []

    if instructions:
        messages.append({"role": "system", "content": instructions})

    if isinstance(input_, str):
        messages.append({"role": "user", "content": input_})
    elif isinstance(input_, list):
        for item in input_:
            if isinstance(item, str):
                messages.append({"role": "user", "content": item})
            elif isinstance(item, dict):
                role = item.get("role", "user")
                content = item.get("content", "")
                if isinstance(content, list):
                    # Content block array – extract plain text parts.
                    parts: list[str] = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") in {"text", "output_text", "input_text"}:
                                parts.append(block.get("text", ""))
                    content = "".join(parts)
                messages.append({"role": role, "content": content})
    else:
        messages.append({"role": "user", "content": str(input_)})

    return messages


def _make_response_envelope(model: str, text: str, usage: dict[str, Any]) -> dict[str, Any]:
    """Build a non-streaming Responses API response object."""
    return {
        "id": f"resp_{uuid.uuid4().hex}",
        "object": "response",
        "created_at": int(time.time()),
        "model": model,
        "status": "completed",
        "output": [
            {
                "id": f"msg_{uuid.uuid4().hex}",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {
                        "type": "output_text",
                        "text": text,
                        "annotations": [],
                    }
                ],
            }
        ],
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
        "error": None,
        "incomplete_details": None,
        "instructions": None,
        "metadata": {},
        "parallel_tool_calls": True,
        "temperature": 1.0,
        "tool_choice": "auto",
        "tools": [],
        "top_p": 1.0,
    }


async def _stream_completions_as_responses(
    completions_url: str,
    payload: dict[str, Any],
    auth_header: str,
    model: str,
):
    """Yield Responses-API SSE events translated from Chat Completions stream."""
    resp_id = f"resp_{uuid.uuid4().hex}"
    item_id = f"msg_{uuid.uuid4().hex}"
    created_at = int(time.time())

    def sse(event: str, data: dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    # --- response.created ---
    yield sse(
        "response.created",
        {
            "type": "response.created",
            "response": {
                "id": resp_id,
                "object": "response",
                "created_at": created_at,
                "model": model,
                "status": "in_progress",
                "output": [],
            },
        },
    )

    # --- response.output_item.added ---
    yield sse(
        "response.output_item.added",
        {
            "type": "response.output_item.added",
            "output_index": 0,
            "item": {
                "id": item_id,
                "type": "message",
                "role": "assistant",
                "status": "in_progress",
                "content": [],
            },
        },
    )

    # --- response.content_part.added ---
    yield sse(
        "response.content_part.added",
        {
            "type": "response.content_part.added",
            "item_id": item_id,
            "output_index": 0,
            "content_index": 0,
            "part": {"type": "output_text", "text": "", "annotations": []},
        },
    )

    full_text = ""
    usage: dict[str, Any] = {}

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            completions_url,
            json=payload,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
            },
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                yield sse(
                    "error",
                    {"type": "error", "code": resp.status_code, "message": body.decode()},
                )
                return

            async for raw_line in resp.aiter_lines():
                line = raw_line.strip()
                if not line or not line.startswith("data:"):
                    continue
                chunk_str = line[len("data:"):].strip()
                if chunk_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(chunk_str)
                except json.JSONDecodeError:
                    continue

                delta_content = (
                    (chunk.get("choices") or [{}])[0]
                    .get("delta", {})
                    .get("content") or ""
                )
                if delta_content:
                    full_text += delta_content
                    yield sse(
                        "response.output_text.delta",
                        {
                            "type": "response.output_text.delta",
                            "item_id": item_id,
                            "output_index": 0,
                            "content_index": 0,
                            "delta": delta_content,
                        },
                    )

                if chunk.get("usage"):
                    usage = chunk["usage"]

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)

    # --- response.output_text.done ---
    yield sse(
        "response.output_text.done",
        {
            "type": "response.output_text.done",
            "item_id": item_id,
            "output_index": 0,
            "content_index": 0,
            "text": full_text,
        },
    )

    # --- response.output_item.done ---
    yield sse(
        "response.output_item.done",
        {
            "type": "response.output_item.done",
            "output_index": 0,
            "item": {
                "id": item_id,
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [
                    {
                        "type": "output_text",
                        "text": full_text,
                        "annotations": [],
                    }
                ],
            },
        },
    )

    # --- response.completed ---
    yield sse(
        "response.completed",
        {
            "type": "response.completed",
            "response": {
                "id": resp_id,
                "object": "response",
                "created_at": created_at,
                "model": model,
                "status": "completed",
                "output": [
                    {
                        "id": item_id,
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": full_text,
                                "annotations": [],
                            }
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": prompt_tokens,
                    "output_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                },
            },
        },
    )


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post("/v1/responses")
async def responses_to_completions(request: Request):
    """Translate an OpenAI Responses API request to Chat Completions.

    Receives ``POST /v1/responses``, converts the payload to
    ``/v1/chat/completions`` format, forwards to LiteLLM, and returns the
    result in the Responses API envelope – both streaming and non-streaming.
    """
    try:
        body: dict[str, Any] = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {exc}") from exc

    model: str = body.get("model", "")
    if not model:
        raise HTTPException(status_code=400, detail="'model' field is required")

    input_ = body.get("input", "")
    instructions: str | None = body.get("instructions")
    skill_id_raw = body.get("skill_id")
    skill_id = str(skill_id_raw).strip() if skill_id_raw is not None else ""

    if skill_id:
        store = getattr(getattr(request.app, "state", None), "store", None)
        if store is None:
            raise HTTPException(status_code=500, detail="Store is not initialized")

        skill = store.get_skill(skill_id)
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        if skill.status != "active":
            raise HTTPException(status_code=400, detail="Skill is not active")

        skill_prompt = (skill.system_prompt or "").strip()
        if skill_prompt:
            instructions = f"{skill_prompt}\n\n{instructions}" if instructions else skill_prompt

    stream: bool = bool(body.get("stream", False))
    max_tokens: int | None = body.get("max_output_tokens") or body.get("max_tokens")

    messages = _input_to_messages(input_, instructions)

    completions_payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }
    if max_tokens:
        completions_payload["max_tokens"] = max_tokens

    # Propagate the client's auth header to LiteLLM.
    auth_header = request.headers.get("Authorization", "")

    completions_url = f"{_LITELLM_INTERNAL_BASE}/v1/chat/completions"

    if stream:
        return StreamingResponse(
            _stream_completions_as_responses(
                completions_url,
                completions_payload,
                auth_header,
                model,
            ),
            media_type="text/event-stream",
        )

    # Non-streaming path.
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            completions_url,
            json=completions_payload,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    completion = resp.json()
    choice = (completion.get("choices") or [{}])[0]
    text = choice.get("message", {}).get("content", "")
    usage = completion.get("usage", {})

    return _make_response_envelope(model, text, usage)


@router.get("/v1/models")
async def list_models(request: Request):
    """代理 GET /v1/models 到 LiteLLM，返回完整模型列表。
    客户端（copilot、claude code、continue 等）使用与直连原厂完全相同的体验。
    """
    auth_header = request.headers.get("Authorization", "")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{_LITELLM_INTERNAL_BASE}/v1/models",
            headers={"Authorization": auth_header, "Content-Type": "application/json"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """POST /v1/chat/completions with automatic RAG injection.

    Searches active knowledge base and injects relevant context as a system
    message prefix before forwarding the request to LiteLLM.  Both streaming
    and non-streaming modes are supported.
    """
    try:
        body: dict[str, Any] = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {exc}") from exc

    auth_header = request.headers.get("Authorization", "")
    store = getattr(getattr(request.app, "state", None), "store", None)

    messages: list[dict[str, Any]] = list(body.get("messages") or [])

    # Extract last user message as RAG query
    query = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                query = content[:500]
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        query = part.get("text", "")[:500]
                        break
            break

    # RAG injection: search knowledge base and prepend as context
    if query and store is not None:
        context_parts: list[str] = []
        try:
            knowledge_records = store.search_knowledge(query=query, limit=3)
            for rec in knowledge_records:
                if rec.content:
                    header = f"### {rec.title}" if rec.title else "### 知识条目"
                    context_parts.append(f"{header}\n{rec.content[:800]}")
        except Exception:
            pass  # RAG failure must never block the request

        if context_parts:
            rag_block = (
                "--- 相关知识库内容（供参考，如与用户问题无关可忽略）---\n"
                + "\n\n".join(context_parts)
                + "\n---"
            )
            sys_msg = next((m for m in messages if m.get("role") == "system"), None)
            if sys_msg:
                sys_msg["content"] = rag_block + "\n\n" + (sys_msg.get("content") or "")
            else:
                messages = [{"role": "system", "content": rag_block}] + messages
            body["messages"] = messages

    stream: bool = bool(body.get("stream", False))
    completions_url = f"{_LITELLM_INTERNAL_BASE}/v1/chat/completions"

    if stream:
        async def _stream_gen():
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream(
                    "POST",
                    completions_url,
                    json=body,
                    headers={"Authorization": auth_header, "Content-Type": "application/json"},
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk

        return StreamingResponse(_stream_gen(), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            completions_url,
            json=body,
            headers={"Authorization": auth_header, "Content-Type": "application/json"},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.api_route("/v1/{rest_of_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_v1_passthrough(request: Request, rest_of_path: str):
    """透明代理所有其他 /v1/* 请求到 LiteLLM（通用兜底路由）。"""
    auth_header = request.headers.get("Authorization", "")
    content_type = request.headers.get("Content-Type", "application/json")
    body_bytes: bytes = b""
    if request.method in ("POST", "PUT", "PATCH"):
        body_bytes = await request.body()

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.request(
            method=request.method,
            url=f"{_LITELLM_INTERNAL_BASE}/v1/{rest_of_path}",
            content=body_bytes or None,
            headers={"Authorization": auth_header, "Content-Type": content_type},
            params=dict(request.query_params),
        )

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
