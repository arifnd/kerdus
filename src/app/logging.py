from __future__ import annotations

import sys
from contextvars import ContextVar

from loguru import logger

from .config import parse_loglevel
from .settings import get_settings, redact

_request_id_var: ContextVar[str] = ContextVar("request_id", default="")
_request_id_token: ContextVar[object | None] = ContextVar("request_id_token", default=None)


def set_request_id(request_id: str) -> None:
    _request_id_token.set(_request_id_var.set(request_id))


def clear_request_id() -> None:
    token = _request_id_token.get()
    if token is not None:
        _request_id_var.reset(token)
        _request_id_token.set(None)


def _redact_message(message: str) -> str:
    settings = get_settings()
    secrets = [
        settings.telegram_bot_token,
        settings.llm_api_key,
        settings.porkbun_api_key,
        settings.porkbun_secret_key,
    ]
    secrets = [s for s in secrets if s]
    for secret in secrets:
        if secret in message:
            message = message.replace(secret, redact(secret))
    return message


def _sink(message) -> None:
    record = message.record
    level = record["level"].name
    rid = _request_id_var.get()
    rid_part = f" {rid} |" if rid else ""
    line = (
        f"{record['time']:%Y-%m-%d %H:%M:%S} | "
        f"{level: <8} | "
        f"{record['name']} |"
        f"{rid_part} "
        f"{_redact_message(record['message'])}"
    )
    if record["exception"] is not None:
        line += "\n" + record["exception"].__str__()
    sys.stdout.write(line + "\n")


def setup_logging(level: str | None = None) -> None:
    log_level = parse_loglevel(level) if level else parse_loglevel(get_settings().log_level)

    logger.remove()
    logger.add(_sink, level=log_level)
    logger.level(log_level)


def get_logger(name: str):
    return logger.bind(name=name)
