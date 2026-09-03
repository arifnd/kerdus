from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from openai import AsyncOpenAI

from ..logging import get_logger
from ..settings import get_settings

log = get_logger("agent.llm")


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def wants_tool(self) -> bool:
        return bool(self.tool_calls)


@dataclass(frozen=True)
class LLMToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


class LLMClient(Protocol):
    async def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[LLMToolSpec],
    ) -> LLMResponse: ...


class OpenAILLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._model = settings.llm_model
        kwargs: dict[str, Any] = {"api_key": settings.llm_api_key}
        if settings.llm_base_url:
            kwargs["base_url"] = settings.llm_base_url
        self._client = AsyncOpenAI(**kwargs)

    async def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[LLMToolSpec],
    ) -> LLMResponse:
        tool_specs = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in tools
        ]

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tool_specs if tool_specs else None,
        )

        message = response.choices[0].message
        tool_calls = []
        for tc in message.tool_calls or []:
            name = tc.function.name
            arguments = {}
            if tc.function.arguments:
                import json

                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError as exc:
                    log.warning("failed to parse tool arguments for {}: {}", name, exc)
                    arguments = {}
            tool_calls.append(ToolCall(name=name, arguments=arguments))

        if tool_calls:
            return LLMResponse(tool_calls=tool_calls)
        return LLMResponse(text=message.content or "")

    async def close(self) -> None:
        await self._client.close()
