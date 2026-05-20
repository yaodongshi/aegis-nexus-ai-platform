from __future__ import annotations

from .server import MCPServer


def main() -> None:
    server = MCPServer()
    server.run_stdio()


if __name__ == "__main__":
    main()
