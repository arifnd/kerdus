from __future__ import annotations

import pytest

from app.agent.agent import Agent
from app.agent.llm import LLMResponse, ToolCall
from app.tools import LocalTool, build_local_tools


class FakeLLM:
    def __init__(self, script: list[LLMResponse]) -> None:
        self.script = list(script)
        self.calls = []

    async def complete(self, messages, tools):
        self.calls.append((messages, tools))
        if not self.script:
            return LLMResponse(text="done")
        return self.script.pop(0)


def make_agent(llm: FakeLLM, max_iterations: int = 5, max_tool_result_chars: int = 4000) -> Agent:
    local_tools = build_local_tools(enabled=True)
    return Agent(
        llm=llm,
        local_tools=local_tools,
        max_iterations=max_iterations,
        max_tool_result_chars=max_tool_result_chars,
    )


@pytest.mark.asyncio
async def test_no_tool_needed_returns_text() -> None:
    llm = FakeLLM([LLMResponse(text="Hello there")])
    agent = make_agent(llm)
    assert await agent.handle("hi") == "Hello there"


@pytest.mark.asyncio
async def test_single_local_tool_call() -> None:
    llm = FakeLLM(
        [
            LLMResponse(tool_calls=[ToolCall(name="porkbun_list_domains", arguments={})]),
            LLMResponse(text="You have 3 domains."),
        ]
    )
    agent = make_agent(llm)
    result = await agent.handle("list my domains")
    assert result == "You have 3 domains."


@pytest.mark.asyncio
async def test_max_iterations_exceeded() -> None:
    class LoopLLM:
        def __init__(self):
            self.calls = 0

        async def complete(self, messages, tools):
            self.calls += 1
            return LLMResponse(tool_calls=[ToolCall(name="porkbun_list_domains", arguments={})])

    llm = LoopLLM()
    agent = make_agent(llm, max_iterations=3)
    result = await agent.handle("loop")
    assert "allowed number of steps" in result
    assert llm.calls == 3


@pytest.mark.asyncio
async def test_llm_error_message() -> None:
    class BoomLLM:
        async def complete(self, messages, tools):
            raise RuntimeError("boom")

    agent = make_agent(BoomLLM())
    assert await agent.handle("hi") == "I couldn't process that request right now."


@pytest.mark.asyncio
async def test_unknown_tool_argument_error_relayed() -> None:
    llm = FakeLLM(
        [
            LLMResponse(tool_calls=[ToolCall(name="does_not_exist", arguments={})]),
            LLMResponse(text="ok"),
        ]
    )
    agent = make_agent(llm)
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
                    "name": "porkbun_list_domains",
                    "arguments": "{}",
                },
            }
        ],
    }
    llm = FakeLLM(
        [
            LLMResponse(
                tool_calls=[
                    ToolCall(name="porkbun_list_domains", arguments={}, tool_call_id="call_123")
                ],
                assistant_message=assistant_message,
            ),
            LLMResponse(text="ok"),
        ]
    )
    agent = make_agent(llm)
    await agent.handle("list domains")
    sent = llm.calls[-1][0]
    assert sent[2] == assistant_message
    assert sent[3]["role"] == "tool"
    assert sent[3]["tool_call_id"] == "call_123"


@pytest.mark.asyncio
async def test_invalid_arguments_rejected_by_schema() -> None:
    llm = FakeLLM(
        [
            LLMResponse(
                tool_calls=[ToolCall(name="porkbun_retrieve_records", arguments={"type": "A"})]
            ),
            LLMResponse(text="ok"),
        ]
    )
    agent = make_agent(llm)
    await agent.handle("show records")
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
            return LLMResponse(tool_calls=[ToolCall(name="porkbun_list_domains", arguments={})])

    llm = LoopLLM2()
    agent = make_agent(llm)
    agent.set_max_iterations(2)
    await agent.handle("loop")
    assert llm.calls == 2


@pytest.mark.asyncio
async def test_set_local_tools_setter() -> None:
    async def _noop(**kwargs: object) -> str:
        return "ok"

    custom_tool = LocalTool(
        name="custom_tool",
        description="custom",
        input_schema={"type": "object", "properties": {}},
        func=_noop,
    )
    llm = FakeLLM(
        [
            LLMResponse(tool_calls=[ToolCall(name="custom_tool", arguments={})]),
            LLMResponse(text="done"),
        ]
    )
    agent = make_agent(llm)
    agent.set_local_tools([custom_tool])
    result = await agent.handle("do custom")
    assert result == "done"
