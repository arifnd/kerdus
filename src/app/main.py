from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from .agent.agent import build_agent
from .agent.llm import OpenAILLMClient
from .config import load_config
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


def create_app(
    config_path: str | Path = "config.json",
    state_path: str | Path = "data/schedules.json",
) -> FastAPI:
    setup_logging()
    config = load_config(config_path)
    ctx = AppContext()

    async def lifespan(app: FastAPI):
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
        try:
            await ctx.telegram.start()
            ctx.ready = True
            log.info("application ready")
        except Exception as exc:  # noqa: BLE001 - app can run without the bot up
            log.error("failed to start telegram bot: {}", exc)
            ctx.ready = False

        yield

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

    return app


app = create_app()
