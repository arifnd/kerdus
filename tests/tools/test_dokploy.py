from __future__ import annotations

import pytest

from app.settings import Settings, get_settings
from app.tools.dokploy import tools as dokploy_tools
from app.tools.dokploy.render import (
    render_application,
    render_compose,
    render_notification_add,
    render_notification_delete,
    render_notification_test,
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


NOTIFICATION = {
    "notificationId": "ntf-1",
    "name": "Kerdus Bot",
    "notificationType": "telegram",
    "appDeploy": True,
    "appBuildError": True,
    "databaseBackup": True,
    "volumeBackup": True,
    "dokployRestart": True,
    "dokployBackup": True,
    "dockerCleanup": False,
    "serverThreshold": True,
    "telegram": {
        "telegramId": "tlg-1",
        "botToken": "123456:SUPER_SECRET",
        "chatId": "42",
        "messageThreadId": "",
    },
}


def test_render_notification_add_created() -> None:
    rendered = render_notification_add({"notification": NOTIFICATION, "created": True})
    assert rendered == (
        "Created Telegram notification in Dokploy.\n"
        "Name: Kerdus Bot\n"
        "ID: ntf-1\n"
        "Chat: 42\n"
        "Events enabled:\n"
        "• App deploy\n"
        "• App build error\n"
        "• Database backup\n"
        "• Volume backup\n"
        "• Dokploy restart\n"
        "• Dokploy backup\n"
        "• Server threshold"
    )
    assert "SUPER_SECRET" not in rendered


def test_render_notification_add_already_exists() -> None:
    rendered = render_notification_add({"notification": NOTIFICATION, "created": False})
    assert "Found existing Telegram notification in Dokploy." in rendered
    assert "SUPER_SECRET" not in rendered


def test_render_notification_add_unlisted() -> None:
    rendered = render_notification_add(
        {
            "notification": {
                "name": "Kerdus Bot",
                "notificationId": "",
                "notificationType": "telegram",
            },
            "created": True,
            "listed": False,
        }
    )
    assert rendered == (
        "Created Telegram notification in Dokploy.\n"
        "Name: Kerdus Bot\n"
        "Could not load the notification details from Dokploy. The notification may "
        'still have been created - run "Add dokploy telegram notification" again to '
        "confirm."
    )
    assert "ID:" not in rendered
    assert "Chat:" not in rendered


def test_render_notification_delete() -> None:
    assert render_notification_delete({"notificationId": "ntf-1", "name": "Kerdus Bot"}) == (
        "Deleted Telegram notification: Kerdus Bot\nID: ntf-1"
    )


def test_render_notification_test_success_is_silent() -> None:
    assert render_notification_test({"sent": True, "chat_id": "42", "error": ""}) == ""


def test_render_notification_test_failure() -> None:
    assert render_notification_test(
        {"sent": False, "chat_id": "42", "error": "Error testing the notification"}
    ) == (
        "Could not send the test Telegram message to chat 42.\n"
        "Error: Error testing the notification"
    )


def _env_telegram(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:SUPER_SECRET")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_ID", "42")
    get_settings.cache_clear()


async def test_add_telegram_notification_creates_when_missing(monkeypatch) -> None:
    _env_telegram(monkeypatch)
    created_payloads: list[dict] = []

    async def _bot_name() -> str:
        return "Kerdus Bot"

    async def _list_notifications() -> list[dict]:
        return [NOTIFICATION] if created_payloads else []

    async def _create(payload: dict) -> None:
        created_payloads.append(payload)

    monkeypatch.setattr(dokploy_tools, "get_bot_name", _bot_name)
    monkeypatch.setattr(dokploy_tools, "list_notifications", _list_notifications)
    monkeypatch.setattr(dokploy_tools, "create_telegram_notification", _create)
    result = await dokploy_tools.add_telegram_notification()
    assert result["created"] is True
    assert result["notification"] == NOTIFICATION
    assert created_payloads
    payload = created_payloads[0]
    assert payload["name"] == "Kerdus Bot"
    assert payload["botToken"] == "123456:SUPER_SECRET"
    assert payload["chatId"] == "42"
    assert payload["messageThreadId"] == ""
    assert all(
        payload[k] is True
        for k in (
            "appDeploy",
            "appBuildError",
            "databaseBackup",
            "volumeBackup",
            "dokployRestart",
            "dokployBackup",
            "dockerCleanup",
            "serverThreshold",
        )
    )


async def test_add_telegram_notification_returns_existing(monkeypatch) -> None:
    _env_telegram(monkeypatch)

    async def _bot_name() -> str:
        return "Kerdus Bot"

    async def _create(payload: dict) -> None:  # pragma: no cover - must not be called
        raise AssertionError("should reuse the existing notification")

    async def _list_notifications() -> list[dict]:
        return [NOTIFICATION]

    monkeypatch.setattr(dokploy_tools, "get_bot_name", _bot_name)
    monkeypatch.setattr(dokploy_tools, "list_notifications", _list_notifications)
    monkeypatch.setattr(dokploy_tools, "create_telegram_notification", _create)
    result = await dokploy_tools.add_telegram_notification()
    assert result == {"notification": NOTIFICATION, "created": False}


async def test_add_telegram_notification_creates_when_listing_fails(monkeypatch) -> None:
    _env_telegram(monkeypatch)
    created_payloads: list[dict] = []

    async def _bot_name() -> str:
        return "Kerdus Bot"

    async def _list_notifications() -> list[dict]:
        raise dokploy_tools.DokployAPIError(status=403, message="Forbidden")

    async def _create(payload: dict) -> None:
        created_payloads.append(payload)

    monkeypatch.setattr(dokploy_tools, "get_bot_name", _bot_name)
    monkeypatch.setattr(dokploy_tools, "list_notifications", _list_notifications)
    monkeypatch.setattr(dokploy_tools, "create_telegram_notification", _create)
    result = await dokploy_tools.add_telegram_notification()
    assert result == {
        "notification": {
            "name": "Kerdus Bot",
            "notificationId": "",
            "notificationType": "telegram",
        },
        "created": True,
        "listed": False,
    }
    assert len(created_payloads) == 1


async def test_add_telegram_notification_unlisted_after_create(monkeypatch) -> None:
    _env_telegram(monkeypatch)

    async def _bot_name() -> str:
        return "Kerdus Bot"

    async def _list_notifications() -> list[dict]:
        return []

    created_payloads: list[dict] = []

    async def _create(payload: dict) -> None:
        created_payloads.append(payload)

    monkeypatch.setattr(dokploy_tools, "get_bot_name", _bot_name)
    monkeypatch.setattr(dokploy_tools, "list_notifications", _list_notifications)
    monkeypatch.setattr(dokploy_tools, "create_telegram_notification", _create)
    result = await dokploy_tools.add_telegram_notification()
    assert result["created"] is True
    assert result["listed"] is False
    assert result["notification"]["notificationId"] == ""


async def test_add_telegram_notification_dedupes_by_name_when_relation_missing(
    monkeypatch,
) -> None:
    _env_telegram(monkeypatch)
    flat = {
        "notificationId": "ntf-9",
        "name": "Kerdus Bot",
        "notificationType": "telegram",
    }

    async def _bot_name() -> str:
        return "Kerdus Bot"

    async def _list_notifications() -> list[dict]:
        return [flat]

    async def _create(payload: dict) -> None:  # pragma: no cover - must not be called
        raise AssertionError("should reuse the existing notification")

    monkeypatch.setattr(dokploy_tools, "get_bot_name", _bot_name)
    monkeypatch.setattr(dokploy_tools, "list_notifications", _list_notifications)
    monkeypatch.setattr(dokploy_tools, "create_telegram_notification", _create)
    result = await dokploy_tools.add_telegram_notification()
    assert result == {"notification": flat, "created": False}


async def test_add_telegram_notification_skips_bot_name_when_exists(monkeypatch) -> None:
    _env_telegram(monkeypatch)

    async def _bot_name() -> str:
        raise ValueError("Telegram getMe unreachable")

    async def _list_notifications() -> list[dict]:
        return [NOTIFICATION]

    async def _create(payload: dict) -> None:  # pragma: no cover - must not be called
        raise AssertionError("should reuse the existing notification")

    monkeypatch.setattr(dokploy_tools, "get_bot_name", _bot_name)
    monkeypatch.setattr(dokploy_tools, "list_notifications", _list_notifications)
    monkeypatch.setattr(dokploy_tools, "create_telegram_notification", _create)
    result = await dokploy_tools.add_telegram_notification()
    assert result == {"notification": NOTIFICATION, "created": False}


async def test_add_telegram_notification_succeeds_when_create_raises_after_commit(
    monkeypatch,
) -> None:
    _env_telegram(monkeypatch)
    calls = {"n": 0}

    async def _bot_name() -> str:
        return "Kerdus Bot"

    async def _list_notifications() -> list[dict]:
        calls["n"] += 1
        return [NOTIFICATION] if calls["n"] > 2 else []

    async def _create(payload: dict) -> None:
        raise RuntimeError("read timeout")

    monkeypatch.setattr(dokploy_tools, "get_bot_name", _bot_name)
    monkeypatch.setattr(dokploy_tools, "list_notifications", _list_notifications)
    monkeypatch.setattr(dokploy_tools, "create_telegram_notification", _create)
    result = await dokploy_tools.add_telegram_notification()
    assert result == {"notification": NOTIFICATION, "created": True}


async def test_add_telegram_notification_succeeds_when_create_uncertain_and_unlisted(
    monkeypatch,
) -> None:
    _env_telegram(monkeypatch)

    async def _bot_name() -> str:
        return "Kerdus Bot"

    async def _list_notifications() -> list[dict]:
        return []

    async def _create(payload: dict) -> None:
        raise RuntimeError("connection lost")

    monkeypatch.setattr(dokploy_tools, "get_bot_name", _bot_name)
    monkeypatch.setattr(dokploy_tools, "list_notifications", _list_notifications)
    monkeypatch.setattr(dokploy_tools, "create_telegram_notification", _create)
    result = await dokploy_tools.add_telegram_notification()
    assert result == {
        "notification": {
            "name": "Kerdus Bot",
            "notificationId": "",
            "notificationType": "telegram",
        },
        "created": True,
        "listed": False,
    }


async def test_add_telegram_notification_raises_on_api_error(monkeypatch) -> None:
    _env_telegram(monkeypatch)

    async def _bot_name() -> str:
        return "Kerdus Bot"

    async def _list_notifications() -> list[dict]:
        return []

    async def _create(payload: dict) -> None:
        raise dokploy_tools.DokployAPIError(status=400, message="Error creating the notification")

    monkeypatch.setattr(dokploy_tools, "get_bot_name", _bot_name)
    monkeypatch.setattr(dokploy_tools, "list_notifications", _list_notifications)
    monkeypatch.setattr(dokploy_tools, "create_telegram_notification", _create)
    with pytest.raises(dokploy_tools.DokployAPIError):
        await dokploy_tools.add_telegram_notification()


async def test_add_telegram_notification_requires_credentials(monkeypatch) -> None:
    with pytest.raises(dokploy_tools.DokployAPIError):
        await dokploy_tools.add_telegram_notification()


async def test_delete_telegram_notification_by_id(monkeypatch) -> None:
    removed: list[str] = []

    async def _remove(notification_id: str) -> dict:
        removed.append(notification_id)
        return {"notificationId": notification_id, "name": "Kerdus Bot"}

    monkeypatch.setattr(dokploy_tools, "remove_notification", _remove)
    result = await dokploy_tools.delete_telegram_notification(notification_id="ntf-1")
    assert removed == ["ntf-1"]
    assert result["notificationId"] == "ntf-1"


async def test_delete_telegram_notification_by_env_match(monkeypatch) -> None:
    _env_telegram(monkeypatch)

    async def _bot_name() -> str:
        return "Kerdus Bot"

    async def _list_notifications() -> list[dict]:
        return [NOTIFICATION]

    monkeypatch.setattr(dokploy_tools, "get_bot_name", _bot_name)
    monkeypatch.setattr(dokploy_tools, "list_notifications", _list_notifications)
    removed: list[str] = []

    async def _remove(notification_id: str) -> dict:
        removed.append(notification_id)
        return {"notificationId": notification_id, "name": "Kerdus Bot"}

    monkeypatch.setattr(dokploy_tools, "remove_notification", _remove)
    result = await dokploy_tools.delete_telegram_notification()
    assert removed == ["ntf-1"]
    assert result["notificationId"] == "ntf-1"


async def test_delete_telegram_notification_no_match_raises(monkeypatch) -> None:
    _env_telegram(monkeypatch)

    async def _bot_name() -> str:
        return "Kerdus Bot"

    async def _list_notifications() -> list[dict]:
        return []

    monkeypatch.setattr(dokploy_tools, "get_bot_name", _bot_name)
    monkeypatch.setattr(dokploy_tools, "list_notifications", _list_notifications)
    with pytest.raises(dokploy_tools.DokployAPIError) as exc_info:
        await dokploy_tools.delete_telegram_notification()
    assert exc_info.value.status == 404


async def test_test_telegram_notification(monkeypatch) -> None:
    _env_telegram(monkeypatch)
    captured: list[tuple] = []

    async def _test_connection(bot_token: str, chat_id: str, message_thread_id: str = "") -> bool:
        captured.append((bot_token, chat_id, message_thread_id))
        return True

    monkeypatch.setattr(dokploy_tools, "test_telegram_connection", _test_connection)
    result = await dokploy_tools.test_telegram_notification()
    assert result == {"sent": True, "chat_id": "42", "error": ""}
    assert captured == [("123456:SUPER_SECRET", "42", "")]


async def test_test_telegram_notification_failure_reports_error(monkeypatch) -> None:
    _env_telegram(monkeypatch)

    async def _test_connection(bot_token: str, chat_id: str, message_thread_id: str = "") -> bool:
        raise dokploy_tools.DokployAPIError(status=400, message="Error testing the notification")

    monkeypatch.setattr(dokploy_tools, "test_telegram_connection", _test_connection)
    result = await dokploy_tools.test_telegram_notification()
    assert result == {
        "sent": False,
        "chat_id": "42",
        "error": "Error testing the notification",
    }
