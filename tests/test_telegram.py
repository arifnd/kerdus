from __future__ import annotations

from app.config import TelegramConfig
from app.telegram.bot import TelegramBot


class FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class FakeMessage:
    def __init__(self, text: str, chat_id: int, reply_target: list) -> None:
        self.text = text
        self.chat_id = chat_id
        self._reply_target = reply_target

    async def reply_text(self, text: str) -> None:
        self._reply_target.append(text)


class FakeUpdate:
    def __init__(self, user: FakeUser, message: FakeMessage) -> None:
        self.effective_user = user
        self.effective_message = message


def make_bot(allowed_id: int, handle):
    return TelegramBot(TelegramConfig(allowed_user_id=allowed_id), handle)


class TestTelegramBotAuthorization:
    async def test_authorized_user_is_handled(self) -> None:
        replies: list[str] = []

        async def handler(text: str) -> str:
            return f"echo:{text}"

        bot = make_bot(111, handler)
        msg = FakeMessage("hello", 999, replies)
        await bot._on_message(FakeUpdate(FakeUser(111), msg), None)
        assert replies == ["echo:hello"]
        assert bot._chat_id == 999

    async def test_unauthorized_user_is_ignored(self, caplog) -> None:
        replies: list[str] = []

        async def handler(text: str) -> str:
            return "should not run"

        bot = make_bot(111, handler)
        msg = FakeMessage("hello", 999, replies)
        await bot._on_message(FakeUpdate(FakeUser(222), msg), None)
        assert replies == []

    async def test_handler_error_sends_fallback(self) -> None:
        replies: list[str] = []

        async def handler(text: str) -> str:
            raise RuntimeError("boom")

        bot = make_bot(111, handler)
        msg = FakeMessage("hello", 999, replies)
        await bot._on_message(FakeUpdate(FakeUser(111), msg), None)
        assert replies == ["I couldn't complete that request right now."]
