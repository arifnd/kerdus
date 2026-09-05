from __future__ import annotations

import types
from typing import Self

import pytest

from app.settings import get_settings
from app.telegram import bot_identity
from app.telegram.bot_identity import get_bot_name


@pytest.fixture(autouse=True)
def _clear_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args) -> bool:
        return False

    async def get(self, _url: str) -> _FakeResponse:
        return _FakeResponse(
            {"ok": True, "result": {"id": 1, "first_name": "Kerdus Bot", "username": "kerdusbot"}}
        )


def _fake_httpx(monkeypatch) -> None:
    monkeypatch.setattr(bot_identity, "httpx", types.SimpleNamespace(AsyncClient=_FakeClient))


async def test_get_bot_name_uses_first_name(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:SUPER_SECRET")
    get_settings.cache_clear()
    _fake_httpx(monkeypatch)
    assert await get_bot_name() == "Kerdus Bot"


async def test_get_bot_name_requires_token(monkeypatch) -> None:
    with pytest.raises(ValueError):
        await get_bot_name()
