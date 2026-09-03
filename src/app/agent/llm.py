from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
from openai import AsyncOpenAI

from ..logging import get_logger
from ..settings import get_settings

log = get_logger("agent.llm")


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    tool_call_id: str = ""


@dataclass(frozen=True)
class LLMResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    assistant_message: dict[str, Any] | None = None

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
    def __init__(
        self,
        max_llm_retries: int = 0,
        llm_retry_base_seconds: float = 1.0,
    ) -> None:
        settings = get_settings()
        self._model = settings.llm_model
        self._settings = settings
        self._client: AsyncOpenAI | None = None
        self._max_retries = max_llm_retries
        self._retry_base_seconds = llm_retry_base_seconds

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            settings = self._settings
            if not settings.llm_api_key:
                raise RuntimeError("LLM_API_KEY is not set")
            kwargs: dict[str, Any] = {"api_key": settings.llm_api_key}
            if settings.llm_base_url:
                kwargs["base_url"] = settings.llm_base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

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

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._get_client().chat.completions.create(
                    model=self._model,
                    messages=messages,
                    tools=tool_specs if tool_specs else None,
                )
                return _build_response(response)
            except Exception as exc:
                if not _is_retryable(exc) or attempt >= self._max_retries:
                    raise
                delay = self._retry_base_seconds * (2**attempt)
                log.warning(
                    "LLM transient error, retrying in {:.1f}s (attempt {}): {}",
                    delay,
                    attempt + 1,
                    exc.__class__.__name__,
                )
                await asyncio.sleep(delay)
                last_exc = exc
        raise last_exc  # type: ignore[misc]

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (408, 429, 500, 502, 503, 504)
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and status in (408, 429, 500, 502, 503, 504):
        return True
    code = getattr(exc, "code", None)
    return (
        isinstance(code, str)
        and code.lower() in {"rate_limit_exceeded", "server_error"}
    )


def _build_response(response: Any) -> LLMResponse:
    message = response.choices[0].message
    tool_calls = []
    for tc in message.tool_calls or []:
        name = tc.function.name
        arguments = {}
        if tc.function.arguments:
            try:
                arguments = json.loads(tc.function.arguments)
            except json.JSONDecodeError as exc:
                log.warning("failed to parse tool arguments for {}: {}", name, exc)
                arguments = {}
        tool_calls.append(
            ToolCall(name=name, arguments=arguments, tool_call_id=tc.id or "")
        )

    if tool_calls:
        return LLMResponse(
            tool_calls=tool_calls,
            assistant_message=message.model_dump(exclude_none=True),
        )
    return LLMResponse(text=message.content or "")
