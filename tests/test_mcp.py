from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.config import MCPServerConfig
from app.mcp.client import MCPServerManager, MCPToolError

FAKE_SERVER = str(Path(__file__).parent / "fake_mcp_server.py")
FAKE_CFG = MCPServerConfig(command=sys.executable, args=[FAKE_SERVER])


@pytest.mark.asyncio
async def test_connect_list_and_call_tool() -> None:
    manager = MCPServerManager()
    try:
        await manager.connect_all({"fake": FAKE_CFG})
        tools = await manager.list_tools()
        names = {t.name for t in tools}
        assert "echo" in names
        assert "fail" in names
        assert all(t.server == "fake" for t in tools)

        result = await manager.call_tool("echo", {"text": "hello"})
        assert result == "echo:hello"
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_call_unknown_tool_raises() -> None:
    manager = MCPServerManager()
    try:
        await manager.connect_all({"fake": FAKE_CFG})
        with pytest.raises(MCPToolError):
            await manager.call_tool("nope", {})
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_error_tool_result_raises() -> None:
    manager = MCPServerManager()
    try:
        await manager.connect_all({"fake": FAKE_CFG})
        with pytest.raises(MCPToolError):
            await manager.call_tool("fail", {})
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_call_when_server_unconnected() -> None:
    manager = MCPServerManager()
    with pytest.raises(MCPToolError):
        await manager.call_tool("echo", {})


@pytest.mark.asyncio
async def test_connection_failure_is_isolated() -> None:
    manager = MCPServerManager()
    try:
        bad_cfg = MCPServerConfig(command="definitely-not-a-real-command-that-exists")
        await manager.connect_all({"bad": bad_cfg})
        assert await manager.list_tools() == []
    finally:
        await manager.close()
