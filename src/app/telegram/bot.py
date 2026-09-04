from __future__ import annotations

import asyncio
import secrets
from collections.abc import Awaitable, Callable
from typing import Any

from telegram import Message, Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, MessageHandler, filters

from ..config import TelegramConfig
from ..formatter import markdown_to_telegram_html, split_telegram_message
from ..logging import clear_request_id, get_logger, set_request_id
from ..settings import get_settings

log = get_logger("telegram")

AgentHandler = Callable[[str], Awaitable[str]]

_PLACEHOLDER = "\u2026"


class TelegramBot:
    def __init__(self, config: TelegramConfig, handle_message: AgentHandler) -> None:
        self._config = config
        self._handle_message = handle_message
        self._application: Application | None = None
        self._chat_id: int | None = None
        self._locks: dict[int, asyncio.Lock] = {}
        self._processing_hint = False

    def set_config(self, config: TelegramConfig) -> None:
        self._config = config

    def set_processing_hint(self, enabled: bool) -> None:
        self._processing_hint = enabled

    def _lock_for(self, chat_id: int) -> asyncio.Lock:
        if chat_id not in self._locks:
            self._locks[chat_id] = asyncio.Lock()
        return self._locks[chat_id]

    async def _on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        user = update.effective_user
        if message is None or user is None or message.text is None:
            return

        if user.id != self._config.allowed_user_id:
            log.warning("ignoring message from unauthorized user id={}", user.id)
            return

        self._chat_id = message.chat_id
        lock = self._lock_for(message.chat_id)
        async with lock:
            await self._handle_and_reply(message)

    async def _handle_and_reply(self, message: Message) -> None:
        placeholder_msg: Message | None = None
        set_request_id(secrets.token_hex(4))
        try:
            if self._processing_hint:
                placeholder_msg = await message.reply_text(_PLACEHOLDER)

            reply = await self._handle_message(message.text)

            chunks = split_telegram_message(reply)
            if placeholder_msg:
                await _edit_formatted(placeholder_msg, chunks[0])
                for chunk in chunks[1:]:
                    await _send_formatted(message.reply_text, chunk)
            else:
                for chunk in chunks:
                    await _send_formatted(message.reply_text, chunk)

        except Exception as exc:  # noqa: BLE001 - never crash the handler
            log.error("agent handler error: {}", exc)
            try:
                if placeholder_msg:
                    await placeholder_msg.edit_text("I couldn't complete that request right now.")
                else:
                    await message.reply_text("I couldn't complete that request right now.")
            except Exception as fallback_exc:  # noqa: BLE001
                log.debug("failed to send fallback error: {}", fallback_exc)
        finally:
            clear_request_id()

    async def start(self) -> None:
        token = get_settings().telegram_bot_token
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

        application = ApplicationBuilder().token(token).build()
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message))
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
        lock = self._lock_for(chat_id)
        async with lock:
            try:
                for chunk in split_telegram_message(text):
                    await _send_formatted(
                        lambda t, **kw: self._application.bot.send_message(
                            chat_id=chat_id, text=t, **kw
                        ),
                        chunk,
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


async def _send_formatted(send_fn: Callable[..., Awaitable[Any]], text: str) -> None:
    """Send *text* as formatted HTML, falling back to plain text on failure."""
    html = markdown_to_telegram_html(text)
    try:
        await send_fn(html, parse_mode="HTML")
    except Exception:  # noqa: BLE001 – invalid markup, fall back
        await send_fn(text)


async def _edit_formatted(message: Message, text: str) -> None:
    """Edit *message* with formatted HTML, falling back to plain text."""
    html = markdown_to_telegram_html(text)
    try:
        await message.edit_text(html, parse_mode="HTML")
    except Exception:  # noqa: BLE001 – invalid markup, fall back
        await message.edit_text(text)
