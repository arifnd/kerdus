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


def render_projects(projects: list[Any]) -> str:
    rows: list[dict[str, str]] = []
    for project in projects:
        if isinstance(project, str):
            rows.append({"line": project})
            continue
        if not isinstance(project, dict):
            continue
        name = str(project.get("name") or "")
        project_id = str(project.get("id") or "")
        if name and project_id:
            rows.append({"line": f"{name} ({project_id})"})
        elif name:
            rows.append({"line": name})
        elif project_id:
            rows.append({"line": project_id})
    return _render("projects.html", projects=rows)
