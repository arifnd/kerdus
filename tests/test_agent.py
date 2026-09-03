from __future__ import annotations

import pytest

from app.agent.agent import Agent
from app.agent.llm import LLMResponse, ToolCall
from app.mcp.client import MCPConnectionError, MCPTool
from app.tools import LocalTool, build_local_tools
from app.tools.memory_scheduler import MemorySchedulerService


class FakeLLM:
    def __init__(self, script: list[LLMResponse]) -> None:
        self.script = list(script)
        self.calls = []

    async def complete(self, messages, tools):
        self.calls.append((messages, tools))
        if not self.script:
            return LLMResponse(text="done")
        return self.script.pop(0)


class FakeMCP:
    def __init__(self, tools: list[MCPTool], error: Exception | None = None) -> None:
        self._tools = tools
        self.error = error
        self.calls = []

    async def list_tools(self) -> list[MCPTool]:
        return list(self._tools)

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        if self.error is not None:
            raise self.error
        return f"result-of:{name}"


def make_agent(llm: FakeLLM, mcp: FakeMCP, max_iterations: int = 5, max_tool_result_chars: int = 4000) -> Agent:
    scheduler = MemorySchedulerService()
    return Agent(
        llm=llm,
        mcp=mcp,
        executor=mcp,
        local_tools=build_local_tools(scheduler),
        max_iterations=max_iterations,
        max_tool_result_chars=max_tool_result_chars,
    )


@pytest.mark.asyncio
async def test_no_tool_needed_returns_text() -> None:
    llm = FakeLLM([LLMResponse(text="Hello there")])
    agent = make_agent(llm, FakeMCP([]))
    assert await agent.handle("hi") == "Hello there"


@pytest.mark.asyncio
async def test_single_local_tool_call() -> None:
    llm = FakeLLM(
        [
            LLMResponse(tool_calls=[ToolCall(name="list_scheduled_checks", arguments={})]),
            LLMResponse(text="You have 0 checks."),
        ]
    )
    agent = make_agent(llm, FakeMCP([]))
    result = await agent.handle("show checks")
    assert result == "You have 0 checks."


@pytest.mark.asyncio
async def test_multi_tool_mcp_chain() -> None:
    mcp = FakeMCP(
        tools=[
            MCPTool(
                server="fake",
                name="find_app",
                description="find",
                input_schema={"type": "object", "properties": {}},
            ),
            MCPTool(
                server="fake",
                name="app_status",
                description="status",
                input_schema={"type": "object", "properties": {}},
            ),
        ]
    )
    llm = FakeLLM(
        [
            LLMResponse(tool_calls=[ToolCall(name="find_app", arguments={"name": "api"})]),
            LLMResponse(tool_calls=[ToolCall(name="app_status", arguments={"id": "1"})]),
            LLMResponse(text="The API is healthy."),
        ]
    )
    agent = make_agent(llm, mcp, max_iterations=5)
    assert await agent.handle("check api") == "The API is healthy."
    assert [c[0] for c in mcp.calls] == ["find_app", "app_status"]


@pytest.mark.asyncio
async def test_max_iterations_exceeded() -> None:
    class LoopLLM:
        def __init__(self):
            self.calls = 0

        async def complete(self, messages, tools):
            self.calls += 1
            return LLMResponse(tool_calls=[ToolCall(name="list_scheduled_checks", arguments={})])

    llm = LoopLLM()
    mcp = FakeMCP([])
    agent = make_agent(llm, mcp, max_iterations=3)
    result = await agent.handle("loop")
    assert "allowed number of steps" in result
    assert llm.calls == 3


@pytest.mark.asyncio
async def test_llm_error_message() -> None:
    class BoomLLM:
        async def complete(self, messages, tools):
            raise RuntimeError("boom")

    agent = make_agent(BoomLLM(), FakeMCP([]))
    assert await agent.handle("hi") == "I couldn't process that request right now."


@pytest.mark.asyncio
async def test_mcp_error_is_relayed_to_llm() -> None:
    tool = MCPTool(
        server="fake",
        name="find_app",
        description="find",
        input_schema={"type": "object", "properties": {}},
    )
    mcp = FakeMCP([tool], error=MCPConnectionError("down", server="fake"))
    llm = FakeLLM(
        [
            LLMResponse(tool_calls=[ToolCall(name="find_app", arguments={})]),
            LLMResponse(text="ok"),
        ]
    )
    agent = make_agent(llm, mcp)
    await agent.handle("check apps")
    last_tool_msgs = [m["content"] for m in llm.calls[-1][0]]
    assert any("unavailable" in m for m in last_tool_msgs)


@pytest.mark.asyncio
async def test_unknown_tool_argument_error_relayed() -> None:
    llm = FakeLLM(
        [
            LLMResponse(tool_calls=[ToolCall(name="does_not_exist", arguments={})]),
            LLMResponse(text="ok"),
        ]
    )
    agent = make_agent(llm, FakeMCP([]))
    await agent.handle("do thing")
    last_tool_msgs = [m["content"] for m in llm.calls[-1][0]]
    assert any("Argument error" in m for m in last_tool_msgs)


@pytest.mark.asyncio
async def test_tool_calls_preceded_by_assistant_message() -> None:
    assistant_message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "list_scheduled_checks",
                    "arguments": "{}",
                },
            }
        ],
    }
    llm = FakeLLM(
        [
            LLMResponse(
                tool_calls=[ToolCall(name="list_scheduled_checks", arguments={}, tool_call_id="call_123")],
                assistant_message=assistant_message,
            ),
            LLMResponse(text="ok"),
        ]
    )
    agent = make_agent(llm, FakeMCP([]))
    await agent.handle("show checks")
    sent = llm.calls[-1][0]
    assert sent[2] == assistant_message
    assert sent[3]["role"] == "tool"
    assert sent[3]["tool_call_id"] == "call_123"
    assert "tool_call_id" in sent[3]


@pytest.mark.asyncio
async def test_invalid_arguments_rejected_by_schema() -> None:
    llm = FakeLLM(
        [
            # interval_seconds is required; missing it should fail validation
            LLMResponse(tool_calls=[ToolCall(name="create_uptime_check", arguments={"id": "x", "url": "http://a"})]),
            LLMResponse(text="ok"),
        ]
    )
    agent = make_agent(llm, FakeMCP([]))
    await agent.handle("create check")
    last_tool_msgs = [m["content"] for m in llm.calls[-1][0] if m.get("role") == "tool"]
    assert any("Argument error" in m for m in last_tool_msgs)


@pytest.mark.asyncio
async def test_tool_result_truncated() -> None:
    long_result = "R" * 100

    async def _long_tool(**kwargs: object) -> str:
        return long_result

    local_tool = LocalTool(
        name="long_tool",
        description="returns a long string",
        input_schema={"type": "object", "properties": {}},
        func=_long_tool,
    )
    agent = Agent(
        llm=FakeLLM([]),
        mcp=FakeMCP([]),
        executor=FakeMCP([]),
        local_tools=[local_tool],
        max_iterations=5,
        max_tool_result_chars=50,
    )
    result = await agent._dispatch("long_tool", {})
    assert "truncated" in result
    assert len(result) < len(long_result)


@pytest.mark.asyncio
async def test_set_max_iterations_setter() -> None:
    class LoopLLM2:
        def __init__(self):
            self.calls = 0

        async def complete(self, messages, tools):
            self.calls += 1
            return LLMResponse(tool_calls=[ToolCall(name="list_scheduled_checks", arguments={})])

    llm = LoopLLM2()
    agent = make_agent(llm, FakeMCP([]))
    agent.set_max_iterations(2)
    await agent.handle("loop")
    assert llm.calls == 2
