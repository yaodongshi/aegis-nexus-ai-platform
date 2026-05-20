from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .server import MCPServer

app = FastAPI(title="team-ai-mcp-gateway")
server = MCPServer()


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "ok": True,
        "at": datetime.now(UTC).isoformat(),
    }


@app.post("/rpc")
async def rpc(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error",
                },
            }
        )

    response = server.handle_json_rpc(payload)
    if response is None:
        return JSONResponse(status_code=204, content={})
    return JSONResponse(response)
