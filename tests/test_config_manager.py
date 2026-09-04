from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from app.config_manager import ConfigManager


def _write_config(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture()
def config_data():
    return {
        "telegram": {"allowed_user_id": 111},
        "agent": {"max_iterations": 5},
        "porkbun": {"enabled": True},
    }


@pytest.fixture()
def config_path(tmp_path: Path, config_data) -> Path:
    path = tmp_path / "config.json"
    _write_config(path, config_data)
    return path


class TestConfigManager:
    def test_loads_initial_config(self, config_path, config_data) -> None:
        mgr = ConfigManager(config_path=config_path)
        assert mgr.config.telegram.allowed_user_id == 111
        assert mgr.config.agent.max_iterations == 5

    def test_reload_picks_up_changes(self, config_path) -> None:
        mgr = ConfigManager(config_path=config_path)
        assert mgr.config.telegram.allowed_user_id == 111

        _write_config(
            config_path,
            {
                "telegram": {"allowed_user_id": 999},
                "agent": {"max_iterations": 3},
                "porkbun": {"enabled": True},
            },
        )
        mgr.reload()
        assert mgr.config.telegram.allowed_user_id == 999
        assert mgr.config.agent.max_iterations == 3

    def test_handler_called_on_change(self, config_path) -> None:
        mgr = ConfigManager(config_path=config_path)
        changes = []
        mgr.on_change(
            lambda old, new: changes.append(
                (old.telegram.allowed_user_id, new.telegram.allowed_user_id)
            )
        )
        _write_config(
            config_path,
            {
                "telegram": {"allowed_user_id": 999},
                "agent": {"max_iterations": 5},
                "porkbun": {"enabled": True},
            },
        )
        mgr.reload()
        assert changes == [(111, 999)]

    def test_no_handler_call_on_same_config(self, config_path) -> None:
        mgr = ConfigManager(config_path=config_path)
        changes = []
        mgr.on_change(lambda old, new: changes.append(True))
        mgr.reload()
        assert changes == []

    def test_reload_returns_current_config(self, config_path) -> None:
        mgr = ConfigManager(config_path=config_path)
        _write_config(
            config_path,
            {
                "telegram": {"allowed_user_id": 222},
                "agent": {"max_iterations": 10},
                "porkbun": {"enabled": True},
            },
        )
        cfg = mgr.reload()
        assert cfg.telegram.allowed_user_id == 222

    def test_reload_corrupt_file_raises(self, config_path) -> None:
        mgr = ConfigManager(config_path=config_path)
        _write_config(config_path, {"bad": True})
        with pytest.raises(ValueError):
            mgr.reload()

    async def test_polling_detects_changes(self, config_path) -> None:
        mgr = ConfigManager(config_path=config_path, poll_interval=0.05)
        changes = []
        mgr.on_change(lambda old, new: changes.append(new.telegram.allowed_user_id))

        mgr.start_polling()
        await asyncio.sleep(0.1)

        _write_config(
            config_path,
            {
                "telegram": {"allowed_user_id": 555},
                "agent": {"max_iterations": 5},
                "porkbun": {"enabled": True},
            },
        )

        await asyncio.sleep(0.3)
        await mgr.stop_polling()

        assert mgr.config.telegram.allowed_user_id == 555
        assert 555 in changes
