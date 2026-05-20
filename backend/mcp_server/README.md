# Team AI MCP Server (C1 Skeleton)

This directory contains the first MCP server skeleton for the Team AI Platform.

## Current scope

- Transport: stdio
- HTTP bridge: `/health` + `/rpc`
- Protocol framing: JSON-RPC 2.0 (line-delimited JSON)
- Implemented methods:
  - `initialize`
  - `ping`
  - `tools/list`
  - `tools/call` (`skills.list`, `skills.get_prompt`, `rag.search`, `task_runs.report`, `health.ping`)
  - `resources/list` (`skill://`, `rag://`)
  - `resources/read`
- Stack-aware filtering:
  - workspace markers: `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `__manifest__.py`
  - environment override: `TEAM_AI_MCP_WORKSPACE`

## Run locally

```bash
cd backend
python -m mcp_server.main
```

or HTTP bridge:

```bash
cd backend
python -m uvicorn mcp_server.http_app:app --host 127.0.0.1 --port 8123
```

## Next steps

- C4 follow-up: wire SSE stream mode for IDE-native MCP transports
- C5 follow-up: expand integration script with tool call and resource read assertions
