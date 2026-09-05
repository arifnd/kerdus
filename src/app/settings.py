from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    telegram_allowed_user_id: int = 0
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"
    llm_base_url: str = ""
    porkbun_enabled: bool = True
    porkbun_api_key: str = ""
    porkbun_secret_key: str = ""
    desec_enabled: bool = True
    desec_token: str = ""
    dokploy_enabled: bool = True
    dokploy_url: str = ""
    dokploy_api_key: str = ""
    dokploy_show_secret: bool = False
    agent_processing: bool | None = None
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("dokploy_show_secret", mode="before")
    @classmethod
    def _coerce_show_secret(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return False

    @field_validator("agent_processing", mode="before")
    @classmethod
    def _coerce_processing(cls, value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not normalized:
                return None
            return normalized in {"1", "true", "yes", "on"}
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def redact(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-4:]
