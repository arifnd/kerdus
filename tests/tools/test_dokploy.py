from __future__ import annotations

import pytest

from app.settings import get_settings
from app.tools.dokploy.render import render_project, render_projects


@pytest.fixture(autouse=True)
def _clear_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_render_projects_success() -> None:
    projects = [
        {"id": "proj-1", "name": "blog"},
        {"id": "proj-2", "name": "stats"},
    ]
    assert render_projects(projects) == (
        "Here are the projects in your Dokploy account:\n• blog (proj-1)\n• stats (proj-2)"
    )


def test_render_project_with_env_when_secret_shown(monkeypatch) -> None:
    monkeypatch.setenv("DOKPLOY_SHOW_SECRET", "true")
    get_settings.cache_clear()
    result = {
        "id": "proj-1",
        "name": "BeGrup",
        "applications": [
            {"appId": "app-1", "appName": "web", "env": "DATABASE_URL=postgres://db\nNODE_ENV=prod"},
            {"appId": "app-2", "appName": "api"},
        ],
        "postgres": [
            {"databaseId": "pg-1", "name": "main-db", "env": "POSTGRES_PASSWORD=secret"},
        ],
        "composes": [
            {"composeId": "comp-1", "composeName": "infra", "env": "VERSION=1.0"},
        ],
    }
    assert render_project(result) == (
        "Project: BeGrup\n"
        "ID: proj-1\n"
        "Applications:\n"
        "• web (app-1)\n"
        "  ENV:\n"
        "    DATABASE_URL=postgres://db\n"
        "    NODE_ENV=prod\n"
        "• api (app-2)\n"
        "Databases:\n"
        "• main-db (pg-1)\n"
        "  ENV:\n"
        "    POSTGRES_PASSWORD=secret\n"
        "Compose:\n"
        "• infra (comp-1)\n"
        "  ENV:\n"
        "    VERSION=1.0"
    )


def test_render_project_hides_env_when_secret_hidden() -> None:
    result = {
        "id": "proj-1",
        "name": "BeGrup",
        "applications": [
            {"appId": "app-1", "appName": "web", "env": "DATABASE_URL=postgres://db\nNODE_ENV=prod"},
        ],
        "postgres": [
            {"databaseId": "pg-1", "name": "main-db", "env": "POSTGRES_PASSWORD=secret"},
        ],
        "composes": [
            {"composeId": "comp-1", "composeName": "infra", "env": "VERSION=1.0"},
        ],
    }
    assert render_project(result) == (
        "Project: BeGrup\n"
        "ID: proj-1\n"
        "Applications:\n"
        "• web (app-1)\n"
        "Databases:\n"
        "• main-db (pg-1)\n"
        "Compose:\n"
        "• infra (comp-1)"
    )
