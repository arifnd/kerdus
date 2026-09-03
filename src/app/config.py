from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class TelegramConfig(BaseModel):
    allowed_user_id: int


class AgentConfig(BaseModel):
    max_iterations: int = Field(default=5, ge=1, le=20)


class MCPServerConfig(BaseModel):
    command: str
    args: list[str] = Field(default_factory=list)


class MCPConfig(BaseModel):
    servers: dict[str, MCPServerConfig] = Field(default_factory=dict)


class SchedulerConfig(BaseModel):
    enabled: bool = True


class AppConfig(BaseModel):
    telegram: TelegramConfig
    agent: AgentConfig
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)

    model_config = {"extra": "forbid"}


def load_config(path: str | Path = "config.json") -> AppConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return AppConfig.model_validate(raw)


_bool_map: dict[str, bool] = {
    "1": True,
    "true": True,
    "yes": True,
    "on": True,
    "0": False,
    "false": False,
    "no": False,
    "off": False,
}


def parse_bool(value: str | bool | None, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return _bool_map.get(str(value).strip().lower(), default)


def parse_loglevel(value: str | None) -> str:
    level = (value or "INFO").strip().upper()
    return level if level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"} else "INFO"


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
