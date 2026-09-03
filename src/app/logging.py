from __future__ import annotations

import sys

from loguru import logger

from .config import parse_loglevel
from .settings import get_settings, redact


def _redact_message(message: str) -> str:
    settings = get_settings()
    secrets = [
        settings.telegram_bot_token,
        settings.llm_api_key,
        settings.dokploy_api_key,
    ]
    secrets = [s for s in secrets if s]
    for secret in secrets:
        if secret in message:
            message = message.replace(secret, redact(secret))
    return message


def _sink(message) -> None:
    record = message.record
    level = record["level"].name
    line = (
        f"{record['time']:%Y-%m-%d %H:%M:%S} | "
        f"{level: <8} | "
        f"{record['name']} | "
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
