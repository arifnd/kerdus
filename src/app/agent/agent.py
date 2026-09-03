from __future__ import annotations

import json
from typing import Any, Protocol

from ..logging import get_logger
from ..mcp.client import MCPError, MCPServerManager
from ..tools import LocalTool, build_local_tools
from .llm import LLMClient, LLMToolSpec
from .prompt import SYSTEM_PROMPT

log = get_logger("agent")


class ToolExecutor(Protocol):
    async def call_tool(self, full_name: str, arguments: dict[str, Any]) -> str: ...


class ToolArgumentError(Exception):
    pass


class Agent:
    def __init__(
        self,
        llm: LLMClient,
        mcp: MCPServerManager,
        executor: ToolExecutor,
        local_tools: list[LocalTool],
        max_iterations: int = 5,
    ) -> None:
        self._llm = llm
        self._mcp = mcp
        self._executor = executor
        self._local_tools = local_tools
        self._max_iterations = max_iterations

    async def _toolspecs(self) -> list[LLMToolSpec]:
        specs: list[LLMToolSpec] = [
            LLMToolSpec(
                name=t.name,
                description=t.description,
                input_schema=t.input_schema,
            )
            for t in self._local_tools
        ]
        for tool in await self._mcp.list_tools():
            specs.append(
                LLMToolSpec(
                    name=tool.name,
                    description=tool.description,
                    input_schema=tool.input_schema,
                )
            )
        return specs

    async def _dispatch(self, name: str, arguments: dict[str, Any]) -> str:
        local = next((t for t in self._local_tools if t.name == name), None)
        if local is not None:
            try:
                result = await local.func(**arguments)
            except TypeError as exc:
                raise ToolArgumentError(f"invalid arguments for {name}: {exc}") from exc
            return _stringify(result)

        mcp_names = {t.name for t in await self._mcp.list_tools()}
        if name in mcp_names:
            return await self._executor.call_tool(name, arguments)

        raise ToolArgumentError(f"unknown tool: {name}")

    async def handle(self, user_text: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ]
        tools = await self._toolspecs()

        for _ in range(self._max_iterations):
            try:
                response = await self._llm.complete(messages, tools)
            except Exception as exc:  # noqa: BLE001 - surface as user-facing error
                log.error("LLM error: {}", exc)
                return "I couldn't process that request right now."

            if not response.wants_tool:
                return response.text or ""

            if response.assistant_message is not None:
                messages.append(dict(response.assistant_message))

            for call in response.tool_calls:
                try:
                    result_text = await self._dispatch(call.name, call.arguments)
                except MCPError as exc:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.tool_call_id,
                            "content": mcp_error_message(exc),
                        }
                    )
                    continue
                except ToolArgumentError as exc:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.tool_call_id,
                            "content": f"Argument error: {exc}",
                        }
                    )
                    continue
                except ValueError as exc:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.tool_call_id,
                            "content": f"Error: {exc}",
                        }
                    )
                    continue

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.tool_call_id,
                        "content": result_text,
                    }
                )

        return "I couldn't complete that request in the allowed number of steps. Try being more specific."


def mcp_error_message(exc: MCPError) -> str:
    if exc.kind == "connection_error":
        return "I couldn't complete that request because Dokploy MCP is unavailable."
    if exc.kind == "tool_error":
        return "The service returned an error while performing that action."
    if exc.kind == "timeout":
        return "The request timed out."
    return "An error occurred while performing that action."


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def build_agent(
    llm: LLMClient,
    mcp: MCPServerManager,
    scheduler: Any,
    max_iterations: int,
) -> Agent:
    local_tools = build_local_tools(scheduler)
    return Agent(
        llm=llm,
        mcp=mcp,
        executor=mcp,
        local_tools=local_tools,
        max_iterations=max_iterations,
    )
