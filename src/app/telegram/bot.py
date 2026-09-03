from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, MessageHandler, filters

from ..config import TelegramConfig
from ..formatter import markdown_to_telegram_html
from ..logging import get_logger
from ..settings import get_settings

log = get_logger("telegram")

AgentHandler = Callable[[str], Awaitable[str]]


async def _send_formatted(
    send_fn: Callable[..., Awaitable[Any]], text: str
) -> None:
    """Send *text* as formatted HTML, falling back to plain text on failure."""
    html = markdown_to_telegram_html(text)
    try:
        await send_fn(html, parse_mode="HTML")
    except Exception:  # noqa: BLE001 – invalid markup, fall back
        await send_fn(text)


class TelegramBot:
    def __init__(self, config: TelegramConfig, handle_message: AgentHandler) -> None:
        self._config = config
        self._handle_message = handle_message
        self._application: Application | None = None
        self._chat_id: int | None = None

    async def _on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        user = update.effective_user
        if message is None or user is None or message.text is None:
            return

        if user.id != self._config.allowed_user_id:
            log.warning("ignoring message from unauthorized user id={}", user.id)
            return

        self._chat_id = message.chat_id
        try:
            reply = await self._handle_message(message.text)
            await _send_formatted(message.reply_text, reply)
        except Exception as exc:  # noqa: BLE001 - never crash the handler
            log.error("agent handler error: {}", exc)
            await message.reply_text("I couldn't complete that request right now.")

    async def start(self) -> None:
        token = get_settings().telegram_bot_token
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

        application = ApplicationBuilder().token(token).build()
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
        )
        self._application = application

        await application.initialize()
        await application.start()
        if application.updater:
            await application.updater.start_polling()
        log.info("telegram bot started")

    async def send_alert(self, text: str) -> None:
        if self._application is None:
            log.error("cannot send alert: bot not running")
            return
        chat_id = self._chat_id or self._config.allowed_user_id
        try:
            await _send_formatted(
                lambda t, **kw: self._application.bot.send_message(
                    chat_id=chat_id, text=t, **kw
                ),
                text,
            )
        except Exception as exc:  # noqa: BLE001 - alert failures are non-fatal
            log.error("failed to send alert: {}", exc)

    async def stop(self) -> None:
        if self._application is None:
            return
        application = self._application
        try:
            if application.updater:
                await application.updater.stop()
            await application.stop()
            await application.shutdown()
        except Exception as exc:  # noqa: BLE001 - best-effort cleanup
            log.warning("error stopping telegram bot: {}", exc)
        self._application = None
        log.info("telegram bot stopped")
