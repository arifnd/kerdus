from __future__ import annotations

import time
from pathlib import Path

import httpx
from fastapi import FastAPI, Request

from .agent.agent import build_agent
from .agent.llm import OpenAILLMClient
from .config import AppConfig
from .config_manager import ConfigManager
from .logging import get_logger, setup_logging
from .settings import get_settings
from .telegram.bot import TelegramBot
from .tools import build_local_tools

log = get_logger("main")


class AppContext:
    def __init__(self) -> None:
        self.llm: OpenAILLMClient | None = None
        self.agent = None
        self.telegram: TelegramBot | None = None
        self.ready = False
        self.config_manager: ConfigManager | None = None


def create_app(
    config_path: str | Path = "config.json",
    poll_interval: float = 5.0,
) -> FastAPI:
    setup_logging()
    ctx = AppContext()

    def on_config_change(old: AppConfig, new: AppConfig) -> None:
        _apply_config_change(ctx, old, new)

    async def lifespan(app: FastAPI):
        ctx.config_manager = ConfigManager(config_path=config_path, poll_interval=poll_interval)
        ctx.config_manager.on_change(on_config_change)
        config = ctx.config_manager.config

        ctx.llm = OpenAILLMClient(
            max_llm_retries=config.agent.max_llm_retries,
            llm_retry_base_seconds=config.agent.llm_retry_base_seconds,
        )

        settings = get_settings()
        local_tools = build_local_tools(
            porkbun_enabled=settings.porkbun_enabled,
            desec_enabled=settings.desec_enabled,
            dokploy_enabled=settings.dokploy_enabled,
        )

        ctx.agent = build_agent(
            llm=ctx.llm,
            local_tools=local_tools,
            max_iterations=config.agent.max_iterations,
            max_tool_result_chars=config.agent.max_tool_result_chars,
        )

        ctx.telegram = TelegramBot(
            config=config.telegram,
            handle_message=ctx.agent.handle,
        )
        ctx.telegram.set_processing_hint(config.agent.processing_hint)
        try:
            await ctx.telegram.start()
            ctx.ready = True
            log.info("application ready")
            await ctx.telegram.send_alert("Service is back online.")
        except Exception as exc:  # noqa: BLE001 - app can run without the bot up
            log.error("failed to start telegram bot: {}", exc)
            ctx.ready = False

        ctx.config_manager.start_polling()

        yield

        await ctx.config_manager.stop_polling()
        await ctx.telegram.stop() if ctx.telegram else None
        if ctx.llm:
            await ctx.llm.close()

    app = FastAPI(title="kerdus", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> dict:
        return {
            "status": "ready" if ctx.ready else "not_ready",
            "telegram": ctx.telegram is not None and ctx.ready,
            "llm": await _llm_status(ctx),
        }

    @app.post("/config/reload")
    async def reload_config(request: Request) -> dict:
        if ctx.config_manager is None:
            return {"status": "error", "message": "config manager not initialized"}
        try:
            ctx.config_manager.reload()
            return {"status": "ok", "message": "config reloaded"}
        except Exception as exc:  # noqa: BLE001 - endpoint isolation
            return {"status": "error", "message": str(exc)}

    return app


def _apply_config_change(ctx: AppContext, old: AppConfig, new: AppConfig) -> None:
    if old.telegram.allowed_user_id != new.telegram.allowed_user_id:
        log.info(
            "telegram allowed_user_id changed: {} -> {}",
            old.telegram.allowed_user_id,
            new.telegram.allowed_user_id,
        )
        if ctx.telegram:
            ctx.telegram.set_config(new.telegram)

    if old.agent.processing_hint != new.agent.processing_hint:
        log.info(
            "agent processing_hint changed: {} -> {}",
            old.agent.processing_hint,
            new.agent.processing_hint,
        )
        if ctx.telegram:
            ctx.telegram.set_processing_hint(new.agent.processing_hint)

    if old.agent.max_iterations != new.agent.max_iterations:
        log.info(
            "agent max_iterations changed: {} -> {}",
            old.agent.max_iterations,
            new.agent.max_iterations,
        )
        if ctx.agent:
            ctx.agent.set_max_iterations(new.agent.max_iterations)


_LLM_CACHE_TTL = 30.0
_llm_probe_cache: tuple[float, str] | None = None


async def _llm_status(ctx: AppContext) -> str:
    global _llm_probe_cache
    if ctx.llm is None or not ctx.llm.base_url:
        return "not_configured"
    now = time.monotonic()
    if _llm_probe_cache and now - _llm_probe_cache[0] < _LLM_CACHE_TTL:
        return _llm_probe_cache[1]
    status = "unreachable"
    try:
        async with httpx.AsyncClient(timeout=2.0, follow_redirects=True) as client:
            await client.get(ctx.llm.base_url)
        status = "reachable"
    except Exception:  # noqa: BLE001 - probe failure is non-fatal
        status = "unreachable"
    _llm_probe_cache = (now, status)
    return status


app = create_app()
