from __future__ import annotations

from loguru import logger

from app.config import load_config
from app.logging import _redact_message
from app.settings import get_settings, redact


def test_load_config() -> None:
    cfg = load_config("config.json")
    assert cfg.telegram.allowed_user_id == 123456789
    assert cfg.agent.max_iterations == 5


def test_env_allowed_user_id_overrides_config(monkeypatch) -> None:
    get_settings.cache_clear()
    try:
        monkeypatch.setenv("TELEGRAM_ALLOWED_USER_ID", "987654321")
        cfg = load_config("config.json")
        assert cfg.telegram.allowed_user_id == 987654321
    finally:
        monkeypatch.delenv("TELEGRAM_ALLOWED_USER_ID", raising=False)
        get_settings.cache_clear()


def test_env_processing_true_overrides_config(monkeypatch) -> None:
    get_settings.cache_clear()
    try:
        monkeypatch.setenv("AGENT_PROCESSING", "true")
        cfg = load_config("config.json")
        assert cfg.agent.processing_hint is True
        assert cfg.agent.max_iterations == 5
    finally:
        monkeypatch.delenv("AGENT_PROCESSING", raising=False)
        get_settings.cache_clear()


def test_env_processing_false_overrides_config(monkeypatch) -> None:
    get_settings.cache_clear()
    try:
        monkeypatch.setenv("AGENT_PROCESSING", "false")
        cfg = load_config("config.json")
        assert cfg.agent.processing_hint is False
    finally:
        monkeypatch.delenv("AGENT_PROCESSING", raising=False)
        get_settings.cache_clear()


def test_env_processing_empty_does_not_override(monkeypatch) -> None:
    get_settings.cache_clear()
    try:
        monkeypatch.setenv("AGENT_PROCESSING", "")
        cfg = load_config("config.json")
        assert cfg.agent.processing_hint is False
    finally:
        monkeypatch.delenv("AGENT_PROCESSING", raising=False)
        get_settings.cache_clear()


def test_redact() -> None:
    assert redact("") == ""
    assert redact("short") == "***"
    out = redact("abcdefghijklmnop")
    assert out == "abcd***mnop"
    assert "abcdefghij" not in out


def test_redaction_masks_secrets() -> None:
    settings = get_settings()
    settings.telegram_bot_token = "abcdefghijklmnop"
    masked = _redact_message("token=abcdefghijklmnop end")
    assert "abcdefghijkl" not in masked
    assert "abcd***mnop" in masked


def test_logger_is_bound() -> None:
    bound = logger.bind(name="test.sub")
    assert bound is not None
