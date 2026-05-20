# Team AI MCP Server (C1 Skeleton)

This directory contains the first MCP server skeleton for the Team AI Platform.

## Current scope

- Transport: stdio
- Protocol framing: JSON-RPC 2.0 (line-delimited JSON)
- Implemented methods:
  - `initialize`
  - `ping`
  - `tools/list`
  - `tools/call` (builtin `health.ping`)
  - `resources/list` (empty)
- Placeholder only:
  - `resources/read`

## Run locally

```bash
cd backend
python -m mcp_server.main
```

## Next steps

- C2: add real `tools/*` and `resources/*` adapters for PlatformStore
- C3: detect repository stack and tag-filter skill/resource loading
- C4: add dedicated mcp service into docker-compose
