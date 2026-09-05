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
    }
    path.write_text(json.dumps(config), encoding="utf-8")


@pytest.fixture()
def config_path(tmp_path: Path) -> Path:
    path = tmp_path / "config.json"
    _write_config(path)
    return path


def test_health_and_ready(config_path) -> None:
    app = create_app(config_path=config_path)
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        ready = client.get("/ready")
        assert ready.status_code == 200
        body = ready.json()
        assert body["status"] in {"ready", "not_ready"}
        assert isinstance(body["telegram"], bool)
        assert body["llm"] in {"reachable", "unreachable", "not_configured"}
        assert body["processing_hint"] is False


def test_ready_reports_processing_hint_enabled(config_path, monkeypatch) -> None:
    from app.config import load_config
    from app.settings import get_settings

    get_settings.cache_clear()
    try:
        monkeypatch.setenv("AGENT_PROCESSING", "true")
        cfg = load_config(config_path)
        app = create_app(config_path=config_path)
        with TestClient(app) as client:
            ready = client.get("/ready").json()
            assert ready["processing_hint"] is True
            assert cfg.agent.processing_hint is True
    finally:
        monkeypatch.delenv("AGENT_PROCESSING", raising=False)
        get_settings.cache_clear()


def test_config_reload_endpoint(config_path) -> None:
    app = create_app(config_path=config_path)
    with TestClient(app) as client:
        resp = client.post("/config/reload")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "message": "config reloaded"}


def test_config_reload_endpoint_corrupt(config_path) -> None:
    app = create_app(config_path=config_path)
    with TestClient(app) as client:
        config_path.write_text("{ not json", encoding="utf-8")
        resp = client.post("/config/reload")
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"
