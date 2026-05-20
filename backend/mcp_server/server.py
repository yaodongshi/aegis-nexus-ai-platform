from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable

from app.schemas import TaskRunReportRequest
from app.store import PlatformStore

from .stack import detect_stack_tags, skill_matches_stack

JSON = dict[str, Any]


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: JSON
    handler: Callable[[JSON], JSON]


class MCPServer:
    """MCP stdio server with minimal tools/resources primitives."""

    def __init__(self, store: PlatformStore | None = None) -> None:
        self._store = store or PlatformStore()
        workspace = os.getenv("TEAM_AI_MCP_WORKSPACE", os.getcwd())
        self._workspace = Path(workspace).resolve()
        self._stack_tags = detect_stack_tags(self._workspace)
        self._tools: dict[str, MCPTool] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        self.register_tool(
            MCPTool(
                name="skills.list",
                description="List active skills with optional query.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1},
                    },
                    "additionalProperties": False,
                },
                handler=self._tool_list_skills,
            )
        )
        self.register_tool(
            MCPTool(
                name="skills.get_prompt",
                description="Get system prompt for one skill.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "skill_id": {"type": "string"},
                    },
                    "required": ["skill_id"],
                    "additionalProperties": False,
                },
                handler=self._tool_get_skill_prompt,
            )
        )
        self.register_tool(
            MCPTool(
                name="rag.search",
                description="Search knowledge base with semantic fallback.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                handler=self._tool_search_rag,
            )
        )
        self.register_tool(
            MCPTool(
                name="task_runs.report",
                description=(
                    "Report one task run and generate skill update draft."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "tool_type": {
                            "type": "string",
                            "enum": ["codex", "claude_code", "other"],
                        },
                        "user_id": {"type": "string"},
                        "task_title": {"type": "string"},
                        "summary": {"type": "string"},
                        "error_log": {"type": "string"},
                        "lessons_learned": {"type": "string"},
                        "proposed_skill_name": {"type": "string"},
                        "proposed_system_prompt": {"type": "string"},
                        "proposed_user_prompt_template": {"type": "string"},
                    },
                    "required": ["task_title", "summary"],
                    "additionalProperties": False,
                },
                handler=self._tool_report_task_run,
            )
        )
        self.register_tool(
            MCPTool(
                name="health.ping",
                description="Check MCP server health and timestamp.",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                handler=lambda _args: {
                    "ok": True,
                    "at": datetime.now(UTC).isoformat(),
                },
            )
        )

    def register_tool(self, tool: MCPTool) -> None:
        self._tools[tool.name] = tool

    def run_stdio(self) -> None:
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except Exception:
                self._write(self._error_response(None, -32700, "Parse error"))
                continue

            response = self.handle_json_rpc(request)
            if response is not None:
                self._write(response)

    def handle_json_rpc(self, request: JSON) -> JSON | None:
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}

        if not isinstance(method, str):
            return self._error_response(request_id, -32600, "Invalid Request")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "team-ai-mcp",
                        "version": "0.1.0",
                    },
                    "capabilities": {
                        "tools": {
                            "listChanged": False,
                        },
                        "resources": {
                            "subscribe": False,
                            "listChanged": False,
                        },
                    },
                },
            }

        if method == "notifications/initialized":
            return None

        if method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {},
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.input_schema,
                        }
                        for tool in self._tools.values()
                    ]
                },
            }

        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(name, str) or name not in self._tools:
                return self._error_response(request_id, -32602, "Unknown tool")
            if not isinstance(arguments, dict):
                return self._error_response(
                    request_id,
                    -32602,
                    "Invalid tool arguments",
                )

            try:
                payload = self._tools[name].handler(arguments)
                text = json.dumps(payload, ensure_ascii=False)
            except Exception as exc:
                return self._error_response(
                    request_id,
                    -32000,
                    f"Tool execution failed: {exc}",
                )

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": text,
                        }
                    ],
                    "isError": False,
                },
            }

        if method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "resources": self._resources_list(),
                },
            }

        if method == "resources/read":
            uri = params.get("uri") if isinstance(params, dict) else None
            if not isinstance(uri, str) or not uri.strip():
                return self._error_response(
                    request_id,
                    -32602,
                    "Missing resource uri",
                )
            try:
                contents = self._resources_read(uri.strip())
            except ValueError as exc:
                return self._error_response(request_id, -32602, str(exc))
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "contents": contents,
                },
            }

        return self._error_response(request_id, -32601, "Method not found")

    @staticmethod
    def _write(payload: JSON) -> None:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    @staticmethod
    def _error_response(request_id: Any, code: int, message: str) -> JSON:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

    def _tool_list_skills(self, args: JSON) -> JSON:
        query = str(args.get("query", "")).strip()
        raw_limit = args.get("limit", 20)
        try:
            limit = max(1, min(100, int(raw_limit)))
        except Exception:
            limit = 20

        if query:
            records = self._store.search_skills(query=query, limit=limit * 3)
        else:
            records = self._store.list_skills()[: limit * 3]

        filtered = [
            item for item in records
            if skill_matches_stack(item.tags, self._stack_tags)
        ][:limit]

        return {
            "workspace": str(self._workspace),
            "stack_tags": sorted(self._stack_tags),
            "count": len(filtered),
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "tags": item.tags,
                    "updated_at": item.updated_at.isoformat(),
                }
                for item in filtered
            ],
        }

    def _tool_get_skill_prompt(self, args: JSON) -> JSON:
        skill_id = str(args.get("skill_id", "")).strip()
        if not skill_id:
            raise ValueError("skill_id is required")
        skill = self._store.get_skill(skill_id)
        if skill is None:
            raise ValueError("Skill not found")
        if not skill_matches_stack(skill.tags, self._stack_tags):
            raise ValueError("Skill filtered by current workspace stack")
        return {
            "id": skill.id,
            "name": skill.name,
            "category": skill.category,
            "tags": skill.tags,
            "system_prompt": skill.system_prompt,
            "updated_at": skill.updated_at.isoformat(),
        }

    def _tool_search_rag(self, args: JSON) -> JSON:
        query = str(args.get("query", "")).strip()
        if not query:
            raise ValueError("query is required")
        raw_limit = args.get("limit", 5)
        try:
            limit = max(1, min(20, int(raw_limit)))
        except Exception:
            limit = 5
        records = self._store.search_knowledge(query=query, limit=limit)
        return {
            "query": query,
            "count": len(records),
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "format": item.format,
                    "tags": item.tags,
                    "content_preview": item.content[:240],
                    "updated_at": item.updated_at.isoformat(),
                }
                for item in records
            ],
        }

    def _tool_report_task_run(self, args: JSON) -> JSON:
        payload = TaskRunReportRequest(
            tool_type=str(args.get("tool_type", "codex")),
            user_id=str(args.get("user_id", "unknown")),
            task_title=str(args.get("task_title", "")).strip(),
            summary=str(args.get("summary", "")).strip(),
            error_log=self._opt_str(args.get("error_log")),
            lessons_learned=self._opt_str(args.get("lessons_learned")),
            proposed_skill_name=self._opt_str(args.get("proposed_skill_name")),
            proposed_system_prompt=self._opt_str(
                args.get("proposed_system_prompt")
            ),
            proposed_user_prompt_template=self._opt_str(
                args.get("proposed_user_prompt_template")
            ),
        )
        if not payload.task_title or not payload.summary:
            raise ValueError("task_title and summary are required")
        result = self._store.report_task_run(payload)
        return {
            "task_run_id": result.task_run.id,
            "skill_update_id": result.skill_update.id,
            "skill_update_status": result.skill_update.status,
            "created_at": result.task_run.created_at.isoformat(),
        }

    def _resources_list(self) -> list[JSON]:
        resources: list[JSON] = []
        for skill in self._store.list_skills():
            if not skill_matches_stack(skill.tags, self._stack_tags):
                continue
            resources.append(
                {
                    "uri": f"skill://{skill.id}",
                    "name": skill.name,
                    "description": (
                        skill.description or "Skill prompt resource"
                    ),
                    "mimeType": "application/json",
                }
            )

        for doc in self._store.list_knowledge()[:50]:
            resources.append(
                {
                    "uri": f"rag://{doc.id}",
                    "name": doc.title,
                    "description": "Knowledge document resource",
                    "mimeType": "text/plain",
                }
            )

        return resources

    def _resources_read(self, uri: str) -> list[JSON]:
        if uri.startswith("skill://"):
            skill_id = uri.removeprefix("skill://").strip()
            skill = self._store.get_skill(skill_id)
            if skill is None:
                raise ValueError("Skill resource not found")
            if not skill_matches_stack(skill.tags, self._stack_tags):
                raise ValueError("Skill resource filtered by workspace stack")
            payload = {
                "id": skill.id,
                "name": skill.name,
                "category": skill.category,
                "tags": skill.tags,
                "system_prompt": skill.system_prompt,
                "updated_at": skill.updated_at.isoformat(),
            }
            return [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(payload, ensure_ascii=False),
                }
            ]

        if uri.startswith("rag://"):
            knowledge_id = uri.removeprefix("rag://").strip()
            record = self._store.get_knowledge(knowledge_id)
            if record is None:
                raise ValueError("Knowledge resource not found")
            return [
                {
                    "uri": uri,
                    "mimeType": "text/plain",
                    "text": record.content,
                }
            ]

        raise ValueError("Unsupported resource uri")

    @staticmethod
    def _opt_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
