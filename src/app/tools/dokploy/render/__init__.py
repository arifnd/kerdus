from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = Path(__file__).parent
_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
    trim_blocks=True,
)


def _render(template: str, **context: Any) -> str:
    return _ENV.get_template(template).render(**context).strip()


def _id_name(value: Any, id_key: str = "id", name_key: str = "name") -> tuple[str, str] | None:
    if isinstance(value, str):
        return (value, value)
    if not isinstance(value, dict):
        return None
    item_id = str(value.get(id_key) or "")
    name = str(value.get(name_key) or "")
    if name and item_id:
        return (item_id, name)
    if name:
        return ("", name)
    if item_id:
        return (item_id, "")
    return None


def _format_items(items: list[Any], id_key: str = "id", name_key: str = "name") -> list[str]:
    lines: list[str] = []
    for item in items:
        pair = _id_name(item, id_key, name_key)
        if pair is None:
            continue
        item_id, name = pair
        if name and item_id:
            lines.append(f"{name} ({item_id})")
        elif name:
            lines.append(name)
        elif item_id:
            lines.append(item_id)
    return lines


def render_projects(result: dict[str, Any]) -> str:
    projects = result if isinstance(result, list) else result.get("projects", [])
    rows = _format_items(projects)
    return _render("projects.html", projects=rows)


def render_project(result: dict[str, Any]) -> str:
    project = result if isinstance(result, dict) else {}
    name = str(project.get("name") or "")
    project_id = str(project.get("id") or "")
    apps = _format_items(
        [
            {"id": app.get("appId"), "name": app.get("appName")}
            for app in project.get("applications", [])
            if isinstance(app, dict)
        ]
    )
    composes = _format_items(
        [
            {"id": c.get("composeId"), "name": c.get("composeName")}
            for c in project.get("composes", [])
            if isinstance(c, dict)
        ]
    )
    databases = _format_items(
        [
            {"id": db.get("databaseId"), "name": db.get("name")}
            for db in project.get("databases", [])
            if isinstance(db, dict)
        ]
    )
    return _render(
        "project.html",
        name=name,
        project_id=project_id,
        apps=apps,
        composes=composes,
        databases=databases,
    )


def render_application(result: dict[str, Any]) -> str:
    app = result if isinstance(result, dict) else {}
    name = str(app.get("appName") or app.get("name") or app.get("projectName") or "")
    app_id = str(app.get("appId") or app.get("id") or "")
    status = str(app.get("appStatus") or "")
    domains = [
        str(d) for d in app.get("domains", []) if isinstance(d, str)
    ]
    description = app.get("description")
    if not isinstance(description, str):
        description = ""
    return _render(
        "application.html",
        name=name,
        application_id=app_id,
        status=status,
        domains=domains,
        description=description,
    )


def render_compose(result: dict[str, Any]) -> str:
    compose = result if isinstance(result, dict) else {}
    name = str(compose.get("composeName") or compose.get("name") or compose.get("projectName") or "")
    compose_id = str(compose.get("composeId") or compose.get("id") or "")
    status = str(compose.get("composeStatus") or "")
    domains = [
        str(d) for d in compose.get("domains", []) if isinstance(d, str)
    ]
    description = compose.get("description")
    if not isinstance(description, str):
        description = ""
    return _render(
        "compose.html",
        name=name,
        compose_id=compose_id,
        status=status,
        domains=domains,
        description=description,
    )


def _render_database(result: dict[str, Any], label: str, template: str) -> str:
    db = result if isinstance(result, dict) else {}
    name = str(db.get("name") or db.get("projectName") or "")
    db_id = str(db.get("databaseId") or db.get("id") or "")
    url = db.get("publicURL") or db.get("internalURL")
    if not isinstance(url, str):
        url = ""
    return _render(template, label=label, name=name, database_id=db_id, url=url)


def render_postgres(result: dict[str, Any]) -> str:
    return _render_database(result, "PostgreSQL", "database.html")


def render_mysql(result: dict[str, Any]) -> str:
    return _render_database(result, "MySQL", "database.html")


def render_mongo(result: dict[str, Any]) -> str:
    return _render_database(result, "MongoDB", "database.html")


def render_mariadb(result: dict[str, Any]) -> str:
    return _render_database(result, "MariaDB", "database.html")


def render_redis(result: dict[str, Any]) -> str:
    return _render_database(result, "Redis", "database.html")
