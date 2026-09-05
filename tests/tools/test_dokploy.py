from __future__ import annotations

from app.tools.dokploy.api import _strip_secrets
from app.tools.dokploy.render import render_projects


def _get_tool(tools, name):
    return next(t for t in tools if t.name == name)


class TestDokployToolSchemas:
    def test_list_projects_has_no_required(self, tools) -> None:
        tool = _get_tool(tools, "dokploy_list_projects")
        assert tool.input_schema.get("required", []) == []

    def test_get_project_requires_project_id(self, tools) -> None:
        tool = _get_tool(tools, "dokploy_get_project")
        assert "project_id" in tool.input_schema["required"]

    def test_get_application_requires_application_id(self, tools) -> None:
        tool = _get_tool(tools, "dokploy_get_application")
        assert "application_id" in tool.input_schema["required"]

    def test_get_compose_requires_compose_id(self, tools) -> None:
        tool = _get_tool(tools, "dokploy_get_compose")
        assert "compose_id" in tool.input_schema["required"]

    def test_get_postgres_requires_postgres_id(self, tools) -> None:
        tool = _get_tool(tools, "dokploy_get_postgres")
        assert "postgres_id" in tool.input_schema["required"]

    def test_get_mysql_requires_mysql_id(self, tools) -> None:
        tool = _get_tool(tools, "dokploy_get_mysql")
        assert "mysql_id" in tool.input_schema["required"]

    def test_get_mongo_requires_mongo_id(self, tools) -> None:
        tool = _get_tool(tools, "dokploy_get_mongo")
        assert "mongo_id" in tool.input_schema["required"]

    def test_get_mariadb_requires_mariadb_id(self, tools) -> None:
        tool = _get_tool(tools, "dokploy_get_mariadb")
        assert "mariadb_id" in tool.input_schema["required"]

    def test_get_redis_requires_redis_id(self, tools) -> None:
        tool = _get_tool(tools, "dokploy_get_redis")
        assert "redis_id" in tool.input_schema["required"]


class TestDokploySecretStripping:
    def test_strips_env_and_secret_keys(self) -> None:
        payload = {
            "id": "app-123",
            "name": "myservice",
            "env": "FOO=bar\nAPI_KEY=secret",
            "buildSecrets": "TOKEN=abc",
            "appName": "foo",
            "password": "p455",
            "normal": {"port": 8080, "replicas": 2},
        }
        stripped = _strip_secrets(payload)
        assert stripped == {
            "id": "app-123",
            "name": "myservice",
            "appName": "foo",
            "normal": {"port": 8080, "replicas": 2},
        }

    def test_strips_recursively_in_lists(self) -> None:
        payload = {"apps": [{"name": "a", "env": "X=1"}]}
        stripped = _strip_secrets(payload)
        assert stripped == {"apps": [{"name": "a"}]}

    def test_strips_nested_secret_key(self) -> None:
        payload = {"config": {"database": {"password": "hunter2", "user": "u"}}}
        stripped = _strip_secrets(payload)
        assert stripped == {"config": {"database": {"user": "u"}}}


class TestDokployRender:
    def test_render_projects(self) -> None:
        projects = [
            {"id": "proj-1", "name": "blog"},
            {"id": "proj-2", "name": "stats"},
        ]
        assert render_projects(projects) == (
            "<code>blog</code> (proj-1)\n<code>stats</code> (proj-2)"
        )

    def test_render_projects_missing_name_or_id(self) -> None:
        assert render_projects([{"name": "no-id"}, {"id": "no-name"}]) == (
            "<code>no-id</code>\n<code>no-name</code>"
        )

    def test_render_projects_empty(self) -> None:
        assert render_projects([]) == "No projects found."