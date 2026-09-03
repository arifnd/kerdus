"""
In-process fake MCP server used by tests.

Spawned as a separate stdio process by the MCP client under test.
Exposes dummy tools:
  - echo(text) -> echoes text back
  - fail()     -> raises, producing an error result
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

server = MCPServer("fake-mcp", version="0.0.1")


@server.tool()
async def echo(text: str) -> str:
    return f"echo:{text}"


@server.tool()
async def fail() -> str:
    raise RuntimeError("boom")


@server.tool()
async def env_value(key: str) -> str:
    import os

    return os.environ.get(key, "")


if __name__ == "__main__":
    import anyio

    anyio.run(server.run_stdio_async)
