from __future__ import annotations

import pytest

from app.settings import Settings, get_settings
from app.tools.dokploy.render import (
    render_application,
    render_compose,
    render_postgres,
    render_project,
    render_projects,
)


@pytest.fixture(autouse=True)
def _clear_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_render_projects_success() -> None:
    projects = [
        {"projectId": "proj-1", "name": "blog"},
        {"projectId": "proj-2", "name": "stats"},
    ]
    assert render_projects(projects) == (
        "Here are the projects in your Dokploy account:\n• blog (proj-1)\n• stats (proj-2)"
    )


def test_render_project_shows_environments_and_services() -> None:
    result = {
        "projectId": "proj-1",
        "name": "BeGrup",
        "environments": [
            {
                "environmentId": "env-1",
                "name": "production",
                "isDefault": True,
                "applications": [
                    {
                        "applicationId": "app-1",
                        "name": "web",
                        "appName": "web-1",
                        "applicationStatus": "idle",
                    },
                    {
                        "applicationId": "app-2",
                        "name": "api",
                        "appName": "api-1",
                        "applicationStatus": "running",
                    },
                ],
                "compose": [
                    {
                        "composeId": "comp-1",
                        "name": "PgWeb",
                        "appName": "pgweb-1",
                        "composeStatus": "idle",
                    },
                ],
                "postgres": [
                    {
                        "postgresId": "pg-1",
                        "name": "main-db",
                        "appName": "main-db-1",
                        "applicationStatus": "idle",
                    },
                ],
            },
            {
                "environmentId": "env-2",
                "name": "staging",
                "isDefault": False,
                "applications": [],
                "compose": [],
                "postgres": [],
            },
        ],
    }
    assert render_project(result) == (
        "Project: BeGrup\n"
        "ID: proj-1\n"
        "Environment: production\n"
        "Applications:\n"
        "• web (app-1)\n"
        "  Status: idle\n"
        "• api (app-2)\n"
        "  Status: running\n"
        "Databases:\n"
        "• main-db (pg-1)\n"
        "  Status: idle\n"
        "Compose:\n"
        "• PgWeb (comp-1)\n"
        "  Status: idle\n"
        "Environment: staging"
    )


def test_show_secret_defaults_false_when_empty(monkeypatch) -> None:
    monkeypatch.setenv("DOKPLOY_SHOW_SECRET", "")
    get_settings.cache_clear()
    assert get_settings().dokploy_show_secret is False


def test_show_secret_false_for_common_falsey(monkeypatch) -> None:
    for value in ("false", "False", "0", "no", "off"):
        monkeypatch.setenv("DOKPLOY_SHOW_SECRET", value)
        get_settings.cache_clear()
        assert get_settings().dokploy_show_secret is False


def test_show_secret_true_for_common_truthy(monkeypatch) -> None:
    for value in ("true", "True", "1", "yes", "on"):
        monkeypatch.setenv("DOKPLOY_SHOW_SECRET", value)
        get_settings.cache_clear()
        assert get_settings().dokploy_show_secret is True


def test_show_secret_false_for_unknown_value(monkeypatch) -> None:
    monkeypatch.setenv("DOKPLOY_SHOW_SECRET", "banana")
    get_settings.cache_clear()
    assert Settings().dokploy_show_secret is False


def test_render_application_hides_env_when_show_secret_empty(monkeypatch) -> None:
    app = {
        "applicationId": "app-1",
        "name": "web",
        "applicationStatus": "running",
        "env": "DATABASE_URL=postgres://db\nNODE_ENV=prod",
    }
    monkeypatch.setenv("DOKPLOY_SHOW_SECRET", "")
    get_settings.cache_clear()
    assert render_application(app) == ("Application: web\nID: app-1\nStatus: running")


def test_render_postgres_hides_env_when_secret_hidden() -> None:
    postgres = {
        "postgresId": "pg-1",
        "name": "BeGrup DB",
        "applicationStatus": "idle",
        "databaseName": "begrup",
        "databaseUser": "admin",
        "env": "POSTGRES_PASSWORD=secret123",
    }
    assert render_postgres(postgres) == (
        "PostgreSQL database: BeGrup DB\nID: pg-1\nStatus: idle\nDatabase: begrup\nUser: admin"
    )


def test_render_application_with_env_when_secret_shown(monkeypatch) -> None:
    monkeypatch.setenv("DOKPLOY_SHOW_SECRET", "true")
    get_settings.cache_clear()
    app = {
        "applicationId": "app-1",
        "name": "web",
        "appName": "web-1",
        "applicationStatus": "running",
        "description": "Main web app",
        "domains": [{"host": "web.example.com"}, {"host": "api.example.com"}],
        "env": "DATABASE_URL=postgres://db\nNODE_ENV=prod",
    }
    assert render_application(app) == (
        "Application: web\n"
        "ID: app-1\n"
        "Status: running\n"
        "Description: Main web app\n"
        "Domains:\n"
        "• web.example.com\n"
        "• api.example.com\n"
        "ENV:\n"
        "  DATABASE_URL=postgres://db\n"
        "  NODE_ENV=prod"
    )


def test_render_application_hides_env_when_secret_hidden() -> None:
    app = {
        "applicationId": "app-1",
        "name": "web",
        "applicationStatus": "running",
        "env": "DATABASE_URL=postgres://db\nNODE_ENV=prod",
    }
    assert render_application(app) == ("Application: web\nID: app-1\nStatus: running")


def test_render_compose_with_env_when_secret_shown(monkeypatch) -> None:
    monkeypatch.setenv("DOKPLOY_SHOW_SECRET", "true")
    get_settings.cache_clear()
    compose = {
        "composeId": "comp-1",
        "name": "PgWeb",
        "composeStatus": "running",
        "description": "PG tools",
        "domains": ["pgweb.example.com"],
        "env": "VERSION=1.0",
    }
    assert render_compose(compose) == (
        "Compose service: PgWeb\n"
        "ID: comp-1\n"
        "Status: running\n"
        "Description: PG tools\n"
        "Domains:\n"
        "• pgweb.example.com\n"
        "ENV:\n"
        "  VERSION=1.0"
    )


def test_render_postgres() -> None:
    postgres = {
        "postgresId": "pg-1",
        "name": "BeGrup DB",
        "applicationStatus": "idle",
        "databaseName": "begrup",
        "databaseUser": "begrup",
        "externalPort": 5432,
    }
    assert render_postgres(postgres) == (
        "PostgreSQL database: BeGrup DB\n"
        "ID: pg-1\n"
        "Status: idle\n"
        "Database: begrup\n"
        "User: begrup\n"
        "Port: 5432"
    )
