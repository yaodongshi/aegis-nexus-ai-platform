from __future__ import annotations

from datetime import UTC, datetime
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, status

from ...task_schemas import (
    TaskCommentCreateRequest,
    TaskCommentRecord,
    TaskCreateRequest,
    TaskHistoryRecord,
    TaskRecord,
    TaskUpdateRequest,
)
from .projects import get_accessible_project
from .users import resolve_user_from_auth_header

router = APIRouter()

_TASKS: dict[str, dict] = {}
_TASK_COMMENTS: dict[str, list[dict]] = {}
_TASK_HISTORY: dict[str, list[dict]] = {}


def _task(task_id: str) -> dict:
    item = _TASKS.get(task_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return item


def _append_history(task_id: str, action: str, detail: str, actor_id: str) -> None:
    _TASK_HISTORY.setdefault(task_id, []).append(
        {
            "id": f"hist_{uuid4().hex[:10]}",
            "task_id": task_id,
            "action": action,
            "detail": detail,
            "actor_id": actor_id,
            "created_at": datetime.now(UTC),
        }
    )


@router.get("/", response_model=List[TaskRecord])
def list_tasks(authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    user_id = current["id"]
    items: list[TaskRecord] = []
    for item in _TASKS.values():
        try:
            get_accessible_project(item["project_id"], user_id)
            items.append(TaskRecord(**item))
        except HTTPException:
            continue
    return items


@router.post("/", response_model=TaskRecord, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreateRequest, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    get_accessible_project(payload.project_id, current["id"])

    now = datetime.now(UTC)
    task_id = f"tsk_{uuid4().hex[:10]}"
    task = {
        "id": task_id,
        "project_id": payload.project_id,
        "title": payload.title.strip(),
        "description": payload.description,
        "assignee_id": payload.assignee_id,
        "status": "todo",
        "priority": payload.priority,
        "created_by": current["id"],
        "created_at": now,
        "updated_at": now,
    }
    _TASKS[task_id] = task
    _append_history(task_id, "created", f"Task created with status={task['status']}", current["id"])
    return TaskRecord(**task)


@router.get("/{task_id}", response_model=TaskRecord)
def get_task(task_id: str, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    task = _task(task_id)
    get_accessible_project(task["project_id"], current["id"])
    return TaskRecord(**task)


@router.put("/{task_id}", response_model=TaskRecord)
def update_task(task_id: str, payload: TaskUpdateRequest, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    task = _task(task_id)
    get_accessible_project(task["project_id"], current["id"])

    updates = payload.model_dump(exclude_none=True)
    old_status = task["status"]
    for key, value in updates.items():
        if key == "title" and isinstance(value, str):
            value = value.strip()
        task[key] = value
    task["updated_at"] = datetime.now(UTC)

    if "status" in updates and updates["status"] != old_status:
        _append_history(
            task_id,
            "status_changed",
            f"Status changed from {old_status} to {updates['status']}",
            current["id"],
        )
    elif updates:
        _append_history(task_id, "updated", "Task fields updated", current["id"])

    return TaskRecord(**task)


@router.post("/{task_id}/comments", response_model=TaskCommentRecord, status_code=status.HTTP_201_CREATED)
def create_comment(
    task_id: str,
    payload: TaskCommentCreateRequest,
    authorization: str | None = Header(default=None),
):
    current = resolve_user_from_auth_header(authorization)
    task = _task(task_id)
    get_accessible_project(task["project_id"], current["id"])

    comment = {
        "id": f"cmt_{uuid4().hex[:10]}",
        "task_id": task_id,
        "user_id": current["id"],
        "content": payload.content,
        "created_at": datetime.now(UTC),
    }
    _TASK_COMMENTS.setdefault(task_id, []).append(comment)
    _append_history(task_id, "commented", "New comment added", current["id"])
    return TaskCommentRecord(**comment)


@router.get("/{task_id}/comments", response_model=List[TaskCommentRecord])
def list_comments(task_id: str, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    task = _task(task_id)
    get_accessible_project(task["project_id"], current["id"])
    return [TaskCommentRecord(**item) for item in _TASK_COMMENTS.get(task_id, [])]


@router.get("/{task_id}/history", response_model=List[TaskHistoryRecord])
def list_history(task_id: str, authorization: str | None = Header(default=None)):
    current = resolve_user_from_auth_header(authorization)
    task = _task(task_id)
    get_accessible_project(task["project_id"], current["id"])
    return [TaskHistoryRecord(**item) for item in _TASK_HISTORY.get(task_id, [])]
