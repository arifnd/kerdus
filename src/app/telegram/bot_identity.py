from __future__ import annotations

import asyncio

import httpx

from ..settings import get_settings


async def get_bot_name() -> str:
    token = get_settings().telegram_bot_token.strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set; cannot determine the bot name")
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                resp.raise_for_status()
                data = resp.json()
            user = data.get("result") or {}
            name = user.get("first_name") or user.get("username") or ""
            if not name:
                raise ValueError("Telegram getMe returned no bot name")
            return name
        except Exception as exc:  # noqa: BLE001 - retry transient network failures
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(0.5 * (attempt + 1))
    raise ValueError("could not fetch the Telegram bot name") from last_error
