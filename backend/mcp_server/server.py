from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable

JSON = dict[str, Any]


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: JSON
    handler: Callable[[JSON], JSON]


class MCPServer:
    """Minimal MCP stdio server skeleton (JSON-RPC 2.0)."""

    def __init__(self) -> None:
        self._tools: dict[str, MCPTool] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
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

            response = self._handle_request(request)
            if response is not None:
                self._write(response)

    def _handle_request(self, request: JSON) -> JSON | None:
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
                    "resources": [],
                },
            }

        if method == "resources/read":
            return self._error_response(
                request_id,
                -32601,
                "Method not implemented",
            )

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
