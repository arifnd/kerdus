from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from ....settings import get_settings

_TEMPLATE_DIR = Path(__file__).parent
_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
    trim_blocks=True,
)


def _render(template: str, **context: Any) -> str:
    return _ENV.get_template(template).render(**context).strip()


def _parse_env(env: Any) -> list[str]:
    if isinstance(env, dict):
        return [f"{k}={v}" for k, v in env.items()]
    if isinstance(env, str):
        return [line.strip() for line in env.split("\n") if line.strip() and "=" in line]
    return []


def _service_env(service: dict[str, Any]) -> list[str]:
    if not get_settings().dokploy_show_secret:
        return []
    return _parse_env(service.get("env"))


def _domain_hosts(domains: Any) -> list[str]:
    if not isinstance(domains, list):
        return []
    hosts: list[str] = []
    for item in domains:
        if isinstance(item, str):
            hosts.append(item)
        elif isinstance(item, dict) and item.get("host"):
            hosts.append(str(item["host"]))
    return hosts


def _str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def render_projects(result: dict[str, Any]) -> str:
    projects = result if isinstance(result, list) else result.get("projects", [])
    lines: list[str] = []
    for project in projects if isinstance(projects, list) else []:
        if not isinstance(project, dict):
            continue
        project_id = _str(project.get("projectId") or project.get("id"))
        name = _str(project.get("name"))
        if name and project_id:
            lines.append(f"{name} ({project_id})")
        elif name:
            lines.append(name)
        elif project_id:
            lines.append(project_id)
    return _render("projects.html", projects=lines)


def _service_summary(items: Any, id_key: str, status_key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        item_id = _str(item.get(id_key))
        name = _str(item.get("name") or item.get("appName"))
        label = f"{name} ({item_id})" if name and item_id else name or item_id
        if not label:
            continue
        rows.append({"label": label, "status": _str(item.get(status_key))})
    return rows


def _database_summary(items: Any, id_key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        item_id = _str(item.get(id_key))
        name = _str(item.get("name") or item.get("appName"))
        label = f"{name} ({item_id})" if name and item_id else name or item_id
        if not label:
            continue
        rows.append({"label": label, "status": _str(item.get("applicationStatus"))})
    return rows


def render_project(result: dict[str, Any]) -> str:
    project = result if isinstance(result, dict) else {}
    name = _str(project.get("name"))
    project_id = _str(project.get("projectId") or project.get("id"))
    environments: list[dict[str, Any]] = []
    for env in (
        project.get("environments", []) if isinstance(project.get("environments"), list) else []
    ):
        if not isinstance(env, dict):
            continue
        environments.append(
            {
                "name": _str(env.get("name")) or _str(env.get("environmentId")) or "default",
                "applications": _service_summary(
                    env.get("applications"), "applicationId", "applicationStatus"
                ),
                "compose": _service_summary(env.get("compose"), "composeId", "composeStatus"),
                "databases": (
                    _database_summary(env.get("postgres"), "postgresId")
                    + _database_summary(env.get("mysql"), "mysqlId")
                    + _database_summary(env.get("mariadb"), "mariadbId")
                    + _database_summary(env.get("mongo"), "mongoId")
                    + _database_summary(env.get("redis"), "redisId")
                    + _database_summary(env.get("libsql"), "libsqlId")
                ),
            }
        )
    return _render(
        "project.html",
        name=name,
        project_id=project_id,
        environments=environments,
    )


def _render_service(template: str, **context: Any) -> str:
    return _render(template, **context)


def render_application(result: dict[str, Any]) -> str:
    app = result if isinstance(result, dict) else {}
    return _render_service(
        "application.html",
        name=_str(app.get("name") or app.get("appName")),
        application_id=_str(app.get("applicationId") or app.get("id")),
        status=_str(app.get("applicationStatus")),
        domains=_domain_hosts(app.get("domains")),
        description=_str(app.get("description")),
        env=_service_env(app),
    )


def render_compose(result: dict[str, Any]) -> str:
    compose = result if isinstance(result, dict) else {}
    return _render_service(
        "compose.html",
        name=_str(compose.get("name") or compose.get("appName")),
        compose_id=_str(compose.get("composeId") or compose.get("id")),
        status=_str(compose.get("composeStatus")),
        domains=_domain_hosts(compose.get("domains")),
        description=_str(compose.get("description")),
        env=_service_env(compose),
    )


def _render_database(result: dict[str, Any], label: str, id_key: str) -> str:
    db = result if isinstance(result, dict) else {}
    return _render_service(
        "database.html",
        label=label,
        name=_str(db.get("name") or db.get("appName")),
        database_id=_str(db.get(id_key) or db.get("id")),
        status=_str(db.get("applicationStatus")),
        database_name=_str(db.get("databaseName")),
        database_user=_str(db.get("databaseUser")),
        external_port=_str(db.get("externalPort")),
        env=_service_env(db),
    )


def render_postgres(result: dict[str, Any]) -> str:
    return _render_database(result, "PostgreSQL", "postgresId")


def render_mysql(result: dict[str, Any]) -> str:
    return _render_database(result, "MySQL", "mysqlId")


def render_mongo(result: dict[str, Any]) -> str:
    return _render_database(result, "MongoDB", "mongoId")


def render_mariadb(result: dict[str, Any]) -> str:
    return _render_database(result, "MariaDB", "mariadbId")


def render_redis(result: dict[str, Any]) -> str:
    return _render_database(result, "Redis", "redisId")


def _notification_context(notification: dict[str, Any]) -> dict[str, Any]:
    telegram = (
        notification.get("telegram") if isinstance(notification.get("telegram"), dict) else {}
    )
    events = [
        ("App deploy", notification.get("appDeploy")),
        ("App build error", notification.get("appBuildError")),
        ("Database backup", notification.get("databaseBackup")),
        ("Volume backup", notification.get("volumeBackup")),
        ("Dokploy restart", notification.get("dokployRestart")),
        ("Dokploy backup", notification.get("dokployBackup")),
        ("Docker cleanup", notification.get("dockerCleanup")),
        ("Server threshold", notification.get("serverThreshold")),
    ]
    enabled = [label for label, on in events if on]
    return {
        "name": _str(notification.get("name")),
        "notification_id": _str(notification.get("notificationId")),
        "chat_id": _str(telegram.get("chatId")),
        "events": enabled,
    }


def render_notification_add(result: dict[str, Any]) -> str:
    notification = result.get("notification", {}) if isinstance(result, dict) else {}
    created = bool(result.get("created")) if isinstance(result, dict) else False
    return _render("notification_add.html", created=created, **_notification_context(notification))


def render_notification_delete(result: dict[str, Any]) -> str:
    notification = result if isinstance(result, dict) else {}
    return _render(
        "notification_delete.html",
        name=_str(notification.get("name")),
        notification_id=_str(notification.get("notificationId")),
    )


def render_notification_test(result: dict[str, Any]) -> str:
    sent = bool(result.get("sent")) if isinstance(result, dict) else False
    chat_id = _str(result.get("chat_id")) if isinstance(result, dict) else ""
    return _render("notification_test.html", sent=sent, chat_id=chat_id)
