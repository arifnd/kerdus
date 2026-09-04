from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

from .config import AppConfig, load_config
from .logging import get_logger

log = get_logger("config")

ChangeHandler = Callable[[AppConfig, AppConfig], None]


class ConfigManager:
    def __init__(self, config_path: str | Path = "config.json", poll_interval: float = 5.0) -> None:
        self._config_path = Path(config_path)
        self._poll_interval = poll_interval
        self._last_mtime: float = 0.0
        self._config: AppConfig = load_config(self._config_path)
        self._handlers: list[ChangeHandler] = []
        self._task: asyncio.Task | None = None

    @property
    def config(self) -> AppConfig:
        return self._config

    def on_change(self, handler: ChangeHandler) -> None:
        self._handlers.append(handler)

    def reload(self) -> AppConfig:
        try:
            new_config = load_config(self._config_path)
        except Exception as exc:
            log.error("failed to reload config from {}: {}", self._config_path, exc)
            raise

        old_config = self._config
        self._config = new_config
        self._last_mtime = self._config_path.stat().st_mtime

        if old_config != new_config:
            log.info("config reloaded from {}", self._config_path)
            for handler in self._handlers:
                try:
                    handler(old_config, new_config)
                except Exception as exc:  # noqa: BLE001 - handler isolation
                    log.warning("config change handler error: {}", exc)
        else:
            log.debug("config unchanged")

        return new_config

    def start_polling(self) -> None:
        self._last_mtime = self._config_path.stat().st_mtime
        self._task = asyncio.create_task(self._poll_loop())

    async def stop_polling(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _poll_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._poll_interval)
                current_mtime = self._config_path.stat().st_mtime
                if current_mtime > self._last_mtime:
                    self.reload()
            except FileNotFoundError:
                log.warning("config file {} not found, skipping poll", self._config_path)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - poll isolation
                log.error("config poll error: {}", exc)
