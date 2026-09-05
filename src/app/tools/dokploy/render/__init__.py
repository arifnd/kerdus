from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = Path(__file__).parent
_ENV = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)


def _render(template: str, **context: Any) -> str:
    return _ENV.get_template(template).render(**context).strip()


def render_projects(projects: list[Any]) -> str:
    rows: list[dict[str, str]] = []
    for project in projects:
        if isinstance(project, str):
            rows.append({"name": project, "id": ""})
            continue
        if not isinstance(project, dict):
            continue
        name = str(project.get("name") or "")
        project_id = str(project.get("id") or "")
        if not name and not project_id:
            continue
        rows.append({"name": name, "id": project_id})
    return _render("projects.html", projects=rows)