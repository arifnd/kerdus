from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..config import MCPServerConfig
from ..logging import get_logger

log = get_logger("mcp")


class MCPError(Exception):
    def __init__(self, kind: str, message: str, *, server: str = ""):
        self.kind = kind
        self.server = server
        super().__init__(message)


class MCPConnectionError(MCPError):
    def __init__(self, message: str, *, server: str = ""):
        super().__init__("connection_error", message, server=server)


class MCPToolError(MCPError):
    def __init__(self, message: str, *, server: str = ""):
        super().__init__("tool_error", message, server=server)


class MCPTimeout(MCPError):
    def __init__(self, message: str, *, server: str = ""):
        super().__init__("timeout", message, server=server)


@dataclass(frozen=True)
class MCPTool:
    server: str
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class MCPSession:
    server_name: str
    session: ClientSession
    _cleanup: Any


class MCPServerManager:
    def __init__(self) -> None:
        self._sessions: dict[str, MCPSession] = {}
        self._tools: dict[str, MCPTool] = {}

    async def connect_all(self, servers: dict[str, MCPServerConfig]) -> None:
        for name, cfg in servers.items():
            try:
                await self._connect(name, cfg)
            except Exception as exc:  # noqa: BLE001 - isolate per-server failures
                log.error("failed to connect to MCP server {}: {}", name, exc)

    async def _connect(self, name: str, cfg: MCPServerConfig) -> None:
        params = StdioServerParameters(command=cfg.command, args=cfg.args)

        read_stream, write_stream = None, None
        cleanup_ctx = stdio_client(params)
        read_stream, write_stream = await cleanup_ctx.__aenter__()

        session_ctx = ClientSession(read_stream, write_stream)
        session = await session_ctx.__aenter__()
        await session.initialize()

        self._sessions[name] = MCPSession(
            server_name=name,
            session=session,
            _cleanup=(cleanup_ctx, session_ctx),
        )

        list_result = await session.list_tools()
        for tool in list_result.tools:
            prefixed = f"{name}__{tool.name}" if tool.name in self._tools else tool.name
            mcp_tool = MCPTool(
                server=name,
                name=prefixed,
                description=tool.description or "",
                input_schema=tool.input_schema,
            )
            self._tools[prefixed] = mcp_tool
            log.debug("registered MCP tool: {}", prefixed)

        log.info("connected to MCP server {} ({} tools)", name, len(list_result.tools))

    async def list_tools(self) -> list[MCPTool]:
        return list(self._tools.values())

    async def call_tool(self, full_name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools.get(full_name)
        if tool is None:
            raise MCPToolError(f"unknown tool: {full_name}")

        session_wrapper = self._sessions.get(tool.server)
        if session_wrapper is None:
            raise MCPConnectionError(
                f"MCP server {tool.server} is not connected",
                server=tool.server,
            )

        session = session_wrapper.session
        tool_name = full_name.split("__", 1)[-1] if "__" in full_name else full_name

        try:
            result = await asyncio.wait_for(
                session.call_tool(tool_name, arguments),
                timeout=60.0,
            )
        except asyncio.TimeoutError:  # noqa: UP041 - asyncio.wait_for raises this
            raise MCPTimeout(
                f"MCP tool {tool_name} timed out",
                server=tool.server,
            )

        if hasattr(result, "is_error") and result.is_error:
            error_text = _extract_text(result)
            raise MCPToolError(
                f"tool {tool_name} failed: {error_text}",
                server=tool.server,
            )

        return _extract_text(result)

    async def close(self) -> None:
        for name, wrapper in self._sessions.items():
            try:
                cleanup_ctx, session_ctx = wrapper._cleanup
                await session_ctx.__aexit__(None, None, None)
                await cleanup_ctx.__aexit__(None, None, None)
                log.debug("closed MCP session {}", name)
            except Exception as exc:  # noqa: BLE001 - best-effort cleanup
                log.warning("error closing MCP session {}: {}", name, exc)
        self._sessions.clear()
        self._tools.clear()


def _extract_text(result: Any) -> str:
    parts: list[str] = []
    for block in getattr(result, "content", []):
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts) if parts else str(result)
