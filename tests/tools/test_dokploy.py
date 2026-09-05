from __future__ import annotations

from app.tools.dokploy.render import render_projects


def test_render_projects_success() -> None:
    projects = [
        {"id": "proj-1", "name": "blog"},
        {"id": "proj-2", "name": "stats"},
    ]
    assert render_projects(projects) == (
        "Here are the projects in your Dokploy account:\n• blog (proj-1)\n• stats (proj-2)"
    )
