from __future__ import annotations

from typing import Any

from ...settings import get_settings
from ...telegram.bot_identity import get_bot_name
from ..base import LocalTool
from .api import (
    DokployAPIError,
    create_telegram_notification,
    get_application,
    get_compose,
    get_mariadb,
    get_mongo,
    get_mysql,
    get_postgres,
    get_project,
    get_redis,
    list_notifications,
    list_projects,
    remove_notification,
    test_telegram_connection,
)
from .render import (
    render_application,
    render_compose,
    render_mariadb,
    render_mongo,
    render_mysql,
    render_notification_add,
    render_notification_delete,
    render_notification_test,
    render_postgres,
    render_project,
    render_redis,
)

__all__ = [
    "DokployAPIError",
    "add_telegram_notification",
    "build_dokploy_tools",
    "delete_telegram_notification",
    "get_application",
    "get_compose",
    "get_mariadb",
    "get_mongo",
    "get_mysql",
    "get_postgres",
    "get_project",
    "get_redis",
    "list_projects",
    "test_telegram_notification",
]


def _telegram_credentials() -> tuple[str, str]:
    settings_obj = get_settings()
    bot_token = settings_obj.telegram_bot_token.strip()
    chat_id = str(settings_obj.telegram_allowed_user_id).strip()
    if not bot_token or not chat_id or chat_id == "0":
        raise DokployAPIError(
            status=400,
            message=(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USER_ID must be set "
                "to manage the Dokploy Telegram notification"
            ),
        )
    return bot_token, chat_id


def _notification_payload(bot_token: str, chat_id: str, name: str) -> dict[str, Any]:
    return {
        "name": name,
        "appDeploy": True,
        "appBuildError": True,
        "databaseBackup": True,
        "volumeBackup": True,
        "dokployRestart": True,
        "dokployBackup": True,
        "dockerCleanup": True,
        "serverThreshold": True,
        "botToken": bot_token,
        "chatId": chat_id,
        "messageThreadId": "",
    }


async def _find_existing_telegram_notification(
    bot_token: str, chat_id: str
) -> dict[str, Any] | None:
    for item in await list_notifications():
        if not isinstance(item, dict):
            continue
        telegram = item.get("telegram")
        if (
            isinstance(telegram, dict)
            and telegram.get("botToken") == bot_token
            and telegram.get("chatId") == chat_id
        ):
            return item
    return None


async def add_telegram_notification() -> dict[str, Any]:
    bot_token, chat_id = _telegram_credentials()
    existing = await _find_existing_telegram_notification(bot_token, chat_id)
    if existing is not None:
        return {"notification": existing, "created": False}
    name = await get_bot_name()
    await create_telegram_notification(_notification_payload(bot_token, chat_id, name))
    found = await _find_existing_telegram_notification(bot_token, chat_id)
    if found is None:
        raise DokployAPIError(
            status=400,
            message=(
                "Notification was created but could not be listed; "
                "make sure the Dokploy API key has notification read permission."
            ),
        )
    return {"notification": found, "created": True}


async def delete_telegram_notification(
    notification_id: str | None = None,
) -> dict[str, Any]:
    if notification_id:
        return await remove_notification(notification_id)
    bot_token, chat_id = _telegram_credentials()
    existing = await _find_existing_telegram_notification(bot_token, chat_id)
    if existing is None:
        raise DokployAPIError(
            status=404,
            message=(
                "No Dokploy Telegram notification matches the bot token and "
                "user id configured in the bot environment."
            ),
        )
    return await remove_notification(str(existing.get("notificationId") or ""))


async def test_telegram_notification() -> dict[str, Any]:
    bot_token, chat_id = _telegram_credentials()
    sent = await test_telegram_connection(bot_token, chat_id)
    return {"sent": sent, "chat_id": chat_id}


def build_dokploy_tools() -> list[LocalTool]:
    return [
        LocalTool(
            name="dokploy_list_projects",
            description=(
                "List all projects with their apps, databases, and compose services. "
                "Returned identifiers are used to fetch further detail with the get_* tools."
            ),
            input_schema={"type": "object", "properties": {}},
            func=list_projects,
        ),
        LocalTool(
            name="dokploy_get_project",
            description="Get project details including all apps, databases, and compose services.",
            input_schema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The project ID.",
                    }
                },
                "required": ["project_id"],
            },
            func=get_project,
            render=render_project,
        ),
        LocalTool(
            name="dokploy_get_application",
            description="Get application details (source, build config, status, domains, etc.).",
            input_schema={
                "type": "object",
                "properties": {
                    "application_id": {
                        "type": "string",
                        "description": "The application ID.",
                    }
                },
                "required": ["application_id"],
            },
            func=get_application,
            render=render_application,
        ),
        LocalTool(
            name="dokploy_get_compose",
            description="Get compose service details (docker-compose config, status, etc.).",
            input_schema={
                "type": "object",
                "properties": {
                    "compose_id": {
                        "type": "string",
                        "description": "The compose service ID.",
                    }
                },
                "required": ["compose_id"],
            },
            func=get_compose,
            render=render_compose,
        ),
        LocalTool(
            name="dokploy_get_postgres",
            description="Get PostgreSQL database details.",
            input_schema={
                "type": "object",
                "properties": {
                    "postgres_id": {
                        "type": "string",
                        "description": "The PostgreSQL database ID.",
                    }
                },
                "required": ["postgres_id"],
            },
            func=get_postgres,
            render=render_postgres,
        ),
        LocalTool(
            name="dokploy_get_mysql",
            description="Get MySQL database details.",
            input_schema={
                "type": "object",
                "properties": {
                    "mysql_id": {
                        "type": "string",
                        "description": "The MySQL database ID.",
                    }
                },
                "required": ["mysql_id"],
            },
            func=get_mysql,
            render=render_mysql,
        ),
        LocalTool(
            name="dokploy_get_mongo",
            description="Get MongoDB database details.",
            input_schema={
                "type": "object",
                "properties": {
                    "mongo_id": {
                        "type": "string",
                        "description": "The MongoDB database ID.",
                    }
                },
                "required": ["mongo_id"],
            },
            func=get_mongo,
            render=render_mongo,
        ),
        LocalTool(
            name="dokploy_get_mariadb",
            description="Get MariaDB database details.",
            input_schema={
                "type": "object",
                "properties": {
                    "mariadb_id": {
                        "type": "string",
                        "description": "The MariaDB database ID.",
                    }
                },
                "required": ["mariadb_id"],
            },
            func=get_mariadb,
            render=render_mariadb,
        ),
        LocalTool(
            name="dokploy_get_redis",
            description="Get Redis database details.",
            input_schema={
                "type": "object",
                "properties": {
                    "redis_id": {
                        "type": "string",
                        "description": "The Redis database ID.",
                    }
                },
                "required": ["redis_id"],
            },
            func=get_redis,
            render=render_redis,
        ),
        LocalTool(
            name="dokploy_add_telegram_notification",
            description=(
                "Create a Telegram notification in Dokploy using the bot token and user id "
                "configured in the bot environment, enabled for all events (deploy, build "
                "errors, backups, restarts, docker cleanup, server thresholds). Returns the "
                "existing notification if one with the same bot token and user id already exists."
            ),
            input_schema={"type": "object", "properties": {}},
            func=add_telegram_notification,
            render=render_notification_add,
        ),
        LocalTool(
            name="dokploy_delete_telegram_notification",
            description=(
                "Delete a Telegram notification in Dokploy. If notification_id is omitted, "
                "the notification matching the bot token and user id configured in the bot "
                "environment is removed."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "notification_id": {
                        "type": "string",
                        "description": (
                            "Optional notification ID. Defaults to the notification configured "
                            "for the bot environment."
                        ),
                    }
                },
            },
            func=delete_telegram_notification,
            render=render_notification_delete,
        ),
        LocalTool(
            name="dokploy_test_telegram_notification",
            description=(
                "Send a test Telegram message via Dokploy to the chat id configured in the "
                "bot environment."
            ),
            input_schema={"type": "object", "properties": {}},
            func=test_telegram_notification,
            render=render_notification_test,
        ),
    ]
