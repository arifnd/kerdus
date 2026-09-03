from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.config import MCPServerConfig
from app.mcp.client import MCPServerManager, MCPToolError, _expand_env

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


@pytest.mark.asyncio
async def test_env_is_forwarded_to_server() -> None:
    manager = MCPServerManager()
    try:
        cfg = MCPServerConfig(
            command=sys.executable,
            args=[FAKE_SERVER],
            env={"ENV_TEST_KEY": "env-value"},
        )
        await manager.connect_all({"fake": cfg})
        result = await manager.call_tool("env_value", {"key": "ENV_TEST_KEY"})
        assert result == "env-value"
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_reconnect_after_close() -> None:
    manager = MCPServerManager()
    manager.reconnect_max_attempts = 1
    try:
        await manager.connect_all({"fake": FAKE_CFG})
        await manager.close_server("fake")
        assert await manager.list_tools() == []
        ok = await manager.reconnect("fake", FAKE_CFG)
        assert ok is True
        result = await manager.call_tool("echo", {"text": "hi"})
        assert result == "echo:hi"
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_tools_retained_after_session_loss_for_lazy_reconnect() -> None:
    manager = MCPServerManager()
    manager.reconnect_max_attempts = 1
    try:
        await manager.connect_all({"fake": FAKE_CFG})
        # Simulate a dead session: remove it while keeping the tool registry.
        await manager._close_server("fake", drop_tools=False)
        # A call for a still-registered tool reconnects on demand.
        result = await manager.call_tool("echo", {"text": "auto"})
        assert result == "echo:auto"
    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_close_server_removes_config() -> None:
    manager = MCPServerManager()
    try:
        await manager.connect_all({"fake": FAKE_CFG})
        await manager.close_server("fake")
        assert await manager.list_tools() == []
    finally:
        await manager.close()


def test_expand_env_resolves_placeholders() -> None:
    import os

    os.environ["EXPAND_TEST"] = "resolved"
    expanded = _expand_env(
        {
            "FOO": "${EXPAND_TEST}",
            "BAR": "$EXPAND_TEST",
            "PLAIN": "literal",
            "MISSING": "${NOPE}",
        }
    )
    assert expanded == {
        "FOO": "resolved",
        "BAR": "resolved",
        "PLAIN": "literal",
        "MISSING": "",
    }
    os.environ.pop("EXPAND_TEST", None)
