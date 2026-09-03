from __future__ import annotations

import asyncio
import os
import re
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
    """Manages MCP server sessions with self-healing reconnect.

    Retains per-server config so a dead session can be re-spawned. Tool names
    are cached per server and invalidated on disconnect/reconnect.
    """

    reconnect_max_attempts: int = 3

    def __init__(self) -> None:
        self._sessions: dict[str, MCPSession] = {}
        self._tools: dict[str, MCPTool] = {}
        self._configs: dict[str, MCPServerConfig] = {}
        self._reconnect_lock = asyncio.Lock()

    async def connect_all(self, servers: dict[str, MCPServerConfig]) -> None:
        for name, cfg in servers.items():
            self._configs[name] = cfg
            try:
                await self._connect(name, cfg)
            except Exception as exc:  # noqa: BLE001 - isolate per-server failures
                log.error("failed to connect to MCP server {}: {}", name, exc)

    async def _connect(self, name: str, cfg: MCPServerConfig) -> None:
        env = {**os.environ, **_expand_env(cfg.env)}
        params = StdioServerParameters(command=cfg.command, args=cfg.args, env=env)

        cleanup_ctx = stdio_client(params)
        read_stream, write_stream = await cleanup_ctx.__aenter__()

        session_ctx = ClientSession(read_stream, write_stream)
        session = await session_ctx.__aenter__()
        await session.initialize()

        # Discover this server's tools before touching the shared cache.
        list_result = await session.list_tools()
        discovered: list[tuple[str, MCPTool]] = []
        for tool in list_result.tools:
            unprefixed = _strip_prefix(tool.name)
            existing = next(
                (t for t in self._tools.values() if t.server == name and t.name == unprefixed),
                None,
            )
            occupied = any(t.name == unprefixed and t.server != name for t in self._tools.values())
            prefixed = (
                f"{name}__{unprefixed}" if (occupied or existing is not None) else unprefixed
            )
            discovered.append(
                (
                    prefixed,
                    MCPTool(
                        server=name,
                        name=prefixed,
                        description=tool.description or "",
                        input_schema=tool.input_schema,
                    ),
                )
            )

        self._sessions[name] = MCPSession(
            server_name=name,
            session=session,
            _cleanup=(cleanup_ctx, session_ctx),
        )
        # Replace this server's tools atomically, keeping other servers' tools.
        for t in list(self._tools.values()):
            if t.server == name:
                del self._tools[t.name]
        for prefixed, mcp_tool in discovered:
            self._tools[prefixed] = mcp_tool
            log.debug("registered MCP tool: {}", prefixed)

        log.info("connected to MCP server {} ({} tools)", name, len(list_result.tools))

    async def reconnect(self, name: str, cfg: MCPServerConfig | None = None) -> bool:
        """Close and re-spawn *name*. Returns True on success."""
        async with self._reconnect_lock:
            await self._close_server(name, drop_tools=False)
            self._configs[name] = cfg or self._configs[name]
            for attempt in range(self.reconnect_max_attempts):
                try:
                    await self._connect(name, self._configs[name])
                    return True
                except Exception as exc:  # noqa: BLE001 - retry with backoff
                    if attempt >= self.reconnect_max_attempts - 1:
                        log.error(
                            "failed to reconnect MCP server {} after {} attempts: {}",
                            name,
                            self.reconnect_max_attempts,
                            exc,
                        )
                        return False
                    delay = 1.0 * (2**attempt)
                    log.warning(
                        "reconnect attempt {} for {} failed ({}), retrying in {:.1f}s",
                        attempt + 1,
                        name,
                        exc.__class__.__name__,
                        delay,
                    )
                    await asyncio.sleep(delay)
            return False

    async def _close_server(self, name: str, *, drop_tools: bool) -> None:
        wrapper = self._sessions.pop(name, None)
        if wrapper is not None:
            try:
                cleanup_ctx, session_ctx = wrapper._cleanup
                await session_ctx.__aexit__(None, None, None)
                await cleanup_ctx.__aexit__(None, None, None)
                log.debug("closed MCP session {}", name)
            except Exception as exc:  # noqa: BLE001 - best-effort cleanup
                log.warning("error closing MCP session {}: {}", name, exc)
        if drop_tools:
            for t in [t for t in self._tools.values() if t.server == name]:
                del self._tools[t.name]
            self._configs.pop(name, None)

    async def close_server(self, name: str) -> None:
        await self._close_server(name, drop_tools=True)

    async def list_tools(self) -> list[MCPTool]:
        return list(self._tools.values())

    def server_status(self) -> dict[str, str]:
        """Return per-server connection status for readiness reporting."""
        status: dict[str, str] = {}
        for name in self._configs:
            status[name] = "connected" if name in self._sessions else "failed"
        return status

    async def call_tool(self, full_name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools.get(full_name)
        if tool is None:
            raise MCPToolError(f"unknown tool: {full_name}")

        session_wrapper = self._sessions.get(tool.server)
        if session_wrapper is None:
            # Server is registered but not connected – try to reconnect once.
            if tool.server in self._configs:
                await self.reconnect(tool.server)
                session_wrapper = self._sessions.get(tool.server)
            if session_wrapper is None:
                raise MCPConnectionError(
                    f"MCP server {tool.server} is not connected",
                    server=tool.server,
                )

        session = session_wrapper.session
        tool_name = _strip_prefix(full_name)

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
        except Exception as exc:
            log.warning("MCP tool {} failed on server {}: {}", tool_name, tool.server, exc)
            await self._close_server(tool.server, drop_tools=False)
            raise MCPConnectionError(
                f"MCP server {tool.server} lost connection",
                server=tool.server,
            ) from exc

        if hasattr(result, "is_error") and result.is_error:
            error_text = _extract_text(result)
            raise MCPToolError(
                f"tool {tool_name} failed: {error_text}",
                server=tool.server,
            )

        return _extract_text(result)

    async def close(self) -> None:
        for name in list(self._sessions.keys()):
            await self._close_server(name, drop_tools=False)
        self._configs.clear()
        self._tools.clear()


def _strip_prefix(name: str) -> str:
    return name.split("__", 1)[-1] if "__" in name else name


_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")


def _expand_env(env: dict[str, str]) -> dict[str, str]:
    expanded: dict[str, str] = {}
    for key, value in env.items():
        expanded[key] = _ENV_PATTERN.sub(
            lambda m: os.environ.get(m.group(1) or m.group(2) or "", ""),
            value,
        )
    return expanded


def _extract_text(result: Any) -> str:
    parts: list[str] = []
    for block in getattr(result, "content", []):
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "\n".join(parts) if parts else str(result)
