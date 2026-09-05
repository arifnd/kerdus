from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from ..logging import get_logger
from ..tools import LocalTool
from .llm import LLMClient, LLMToolSpec
from .prompt import SYSTEM_PROMPT

log = get_logger("agent")


class ToolArgumentError(Exception):
    pass


@dataclass(frozen=True)
class AgentReply:
    text: str
    raw_html: bool = False


class Agent:
    def __init__(
        self,
        llm: LLMClient,
        local_tools: list[LocalTool],
        max_iterations: int = 5,
        max_tool_result_chars: int = 4000,
    ) -> None:
        self._llm = llm
        self._local_tools = local_tools
        self._max_iterations = max_iterations
        self._max_tool_result_chars = max_tool_result_chars

    def set_max_iterations(self, value: int) -> None:
        self._max_iterations = value

    def set_local_tools(self, tools: list[LocalTool]) -> None:
        self._local_tools = tools

    def _schema_for_tool(self, name: str) -> dict[str, Any] | None:
        for t in self._local_tools:
            if t.name == name:
                return t.input_schema
        return None

    async def _validate_arguments(self, name: str, arguments: dict[str, Any]) -> None:
        schema = self._schema_for_tool(name)
        if not schema:
            raise ToolArgumentError(f"unknown tool: {name}")
        errors = sorted(
            Draft202012Validator(schema).iter_errors(arguments),
            key=lambda e: e.path,
        )
        if errors:
            detail = errors[0].message
            raise ToolArgumentError(f"invalid arguments for {name}: {detail}")

    async def _toolspecs(self) -> list[LLMToolSpec]:
        return [
            LLMToolSpec(
                name=t.name,
                description=t.description,
                input_schema=t.input_schema,
            )
            for t in self._local_tools
        ]

    async def _dispatch(self, name: str, arguments: dict[str, Any]) -> AgentReply:
        local = next((t for t in self._local_tools if t.name == name), None)
        if local is not None:
            try:
                result = await local.func(**arguments)
            except TypeError as exc:
                raise ToolArgumentError(f"invalid arguments for {name}: {exc}") from exc
            if local.render is not None:
                return AgentReply(_stringify(local.render(result)), raw_html=True)
            return AgentReply(_truncate(_stringify(result), self._max_tool_result_chars))
        raise ToolArgumentError(f"unknown tool: {name}")

    async def handle(self, user_text: str) -> AgentReply:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ]
        tools = await self._toolspecs()
        iteration = 1

        for _ in range(self._max_iterations):
            try:
                response = await self._llm.complete(messages, tools)
            except Exception as exc:  # noqa: BLE001 - surface as user-facing error
                log.error("LLM error: {}", exc)
                return AgentReply("I couldn't process that request right now.")

            if not response.wants_tool:
                return AgentReply(response.text or "")

            if response.assistant_message is not None:
                messages.append(dict(response.assistant_message))

            for call in response.tool_calls:
                start = asyncio.get_event_loop().time()
                try:
                    await self._validate_arguments(call.name, call.arguments)
                    result = await self._dispatch(call.name, call.arguments)
                    log.debug(
                        "iteration={} tool={} duration_ms={:.0f} result_chars={}",
                        iteration,
                        call.name,
                        (asyncio.get_event_loop().time() - start) * 1000,
                        len(result.text),
                    )
                except ToolArgumentError as exc:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.tool_call_id,
                            "content": f"Argument error: {exc}",
                        }
                    )
                    continue
                except Exception as exc:  # noqa: BLE001
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.tool_call_id,
                            "content": f"Error: {exc}",
                        }
                    )
                    continue

                if result.raw_html:
                    return result
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.tool_call_id,
                        "content": result.text,
                    }
                )

            iteration += 1

        return AgentReply(
            "I couldn't complete that request in the allowed number of steps. Try being more specific."
        )


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n… [truncated]"


def build_agent(
    llm: LLMClient,
    local_tools: list[LocalTool],
    max_iterations: int,
    max_tool_result_chars: int = 4000,
) -> Agent:
    return Agent(
        llm=llm,
        local_tools=local_tools,
        max_iterations=max_iterations,
        max_tool_result_chars=max_tool_result_chars,
    )
