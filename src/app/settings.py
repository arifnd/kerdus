from __future__ import annotations

from functools import lru_cache

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
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def redact(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-4:]
