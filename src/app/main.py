from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request

from .agent.agent import build_agent
from .agent.llm import OpenAILLMClient
from .config import AppConfig
from .config_manager import ConfigManager
from .logging import get_logger, setup_logging
from .mcp.client import MCPServerManager
from .scheduler.scheduler import SchedulerService
from .telegram.bot import TelegramBot

log = get_logger("main")


class AppContext:
    def __init__(self) -> None:
        self.mcp = MCPServerManager()
        self.scheduler: SchedulerService | None = None
        self.llm: OpenAILLMClient | None = None
        self.agent = None
        self.telegram: TelegramBot | None = None
        self.ready = False
        self.config_manager: ConfigManager | None = None


def create_app(
    config_path: str | Path = "config.json",
    state_path: str | Path = "data/schedules.json",
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

        ctx.llm = OpenAILLMClient()

        await ctx.mcp.connect_all(config.mcp.servers)

        ctx.scheduler = SchedulerService(state_path=state_path)
        ctx.scheduler.load_state()
        ctx.scheduler.start()

        ctx.agent = build_agent(
            llm=ctx.llm,
            mcp=ctx.mcp,
            scheduler=ctx.scheduler,
            max_iterations=config.agent.max_iterations,
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
        except Exception as exc:  # noqa: BLE001 - app can run without the bot up
            log.error("failed to start telegram bot: {}", exc)
            ctx.ready = False

        ctx.config_manager.start_polling()

        yield

        await ctx.config_manager.stop_polling()
        await ctx.telegram.stop() if ctx.telegram else None
        if ctx.scheduler:
            ctx.scheduler.shutdown()
        await ctx.mcp.close()
        if ctx.llm:
            await ctx.llm.close()

    app = FastAPI(title="kerdus", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> dict:
        status = "ready" if ctx.ready else "not_ready"
        return {
            "status": status,
            "telegram": ctx.telegram is not None and ctx.ready,
            "scheduler": ctx.scheduler is not None,
            "mcp": len(await ctx.mcp.list_tools()) > 0,
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
        log.info("telegram allowed_user_id changed: {} -> {}", old.telegram.allowed_user_id, new.telegram.allowed_user_id)
        if ctx.telegram:
            ctx.telegram.set_config(new.telegram)

    if old.agent.processing_hint != new.agent.processing_hint:
        log.info("agent processing_hint changed: {} -> {}", old.agent.processing_hint, new.agent.processing_hint)
        if ctx.telegram:
            ctx.telegram.set_processing_hint(new.agent.processing_hint)

    if old.agent.max_iterations != new.agent.max_iterations:
        log.info("agent max_iterations changed: {} -> {}", old.agent.max_iterations, new.agent.max_iterations)
        if ctx.agent:
            ctx.agent._max_iterations = new.agent.max_iterations

    if old.mcp.servers != new.mcp.servers:
        log.warning("mcp servers changed; server reconnect requires restart")

    if old.scheduler.enabled != new.scheduler.enabled:
        log.info("scheduler enabled changed: {} -> {}", old.scheduler.enabled, new.scheduler.enabled)
        if ctx.scheduler:
            if new.scheduler.enabled and not old.scheduler.enabled:
                ctx.scheduler.start()
                log.info("scheduler enabled and started")
            elif not new.scheduler.enabled and old.scheduler.enabled:
                ctx.scheduler.shutdown()
                log.info("scheduler disabled and stopped")


app = create_app()
