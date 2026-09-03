from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def _write_config(path: Path) -> None:
    config = {
        "telegram": {"allowed_user_id": 111},
        "agent": {"max_iterations": 5},
        "mcp": {"servers": {}},
        "scheduler": {"enabled": True},
    }
    path.write_text(json.dumps(config), encoding="utf-8")


@pytest.fixture()
def config_path(tmp_path: Path) -> Path:
    path = tmp_path / "config.json"
    _write_config(path)
    return path


@pytest.fixture()
def state_path(tmp_path: Path) -> Path:
    return tmp_path / "schedules.json"


def test_health_and_ready(config_path, state_path) -> None:
    app = create_app(config_path=config_path, state_path=state_path)
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        ready = client.get("/ready")
        assert ready.status_code == 200
        body = ready.json()
        assert body["status"] in {"ready", "not_ready"}
