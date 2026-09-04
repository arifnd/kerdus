from __future__ import annotations

from app.config import TelegramConfig
from app.telegram.bot import TelegramBot


class FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class FakeSentMessage:
    def __init__(self, replies: list[str]) -> None:
        self._replies = replies
        self.text = replies[-1]

    async def edit_text(self, text: str, **kw: object) -> None:
        self._replies[-1] = text
        self.text = text


class FakeMessage:
    def __init__(self, text: str, chat_id: int, replies: list[str]) -> None:
        self.text = text
        self.chat_id = chat_id
        self._replies = replies

    async def reply_text(self, text: str, **kw: object) -> FakeSentMessage:
        self._replies.append(text)
        return FakeSentMessage(self._replies)


class FakeUpdate:
    def __init__(self, user: FakeUser, message: FakeMessage) -> None:
        self.effective_user = user
        self.effective_message = message


def make_bot(allowed_id: int, handle) -> TelegramBot:
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

    async def test_unauthorized_user_is_ignored(self) -> None:
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

    async def test_processing_hint_sends_placeholder_then_edits(self) -> None:
        replies: list[str] = []

        async def handler(text: str) -> str:
            return "real reply"

        bot = make_bot(111, handler)
        bot.set_processing_hint(True)
        msg = FakeMessage("hello", 999, replies)
        await bot._on_message(FakeUpdate(FakeUser(111), msg), None)
        # placeholder is edited in place: only the final text is visible
        assert replies == ["real reply"]

    async def test_long_reply_chunked(self) -> None:
        replies: list[str] = []

        async def handler(text: str) -> str:
            return "A" * 5000

        bot = make_bot(111, handler)
        msg = FakeMessage("hello", 999, replies)
        await bot._on_message(FakeUpdate(FakeUser(111), msg), None)
        assert len(replies) == 2
        for r in replies:
            assert len(r) <= 4096

    async def test_long_reply_chunked_with_placeholder(self) -> None:
        replies: list[str] = []

        async def handler(text: str) -> str:
            return "B" * 5000

        bot = make_bot(111, handler)
        bot.set_processing_hint(True)
        msg = FakeMessage("hello", 999, replies)
        await bot._on_message(FakeUpdate(FakeUser(111), msg), None)
        # placeholder is edited in place, then a second chunk is sent
        assert len(replies) == 2
        for r in replies:
            assert len(r) <= 4096
