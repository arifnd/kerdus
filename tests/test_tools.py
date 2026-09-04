from __future__ import annotations

import pytest

from app.tools import build_local_tools
from app.tools.desec import DeSecAPIError
from app.tools.dokploy import DokployAPIError
from app.tools.porkbun import PorkbunAPIError


def _get_tool(tools, name):
    return next(t for t in tools if t.name == name)


@pytest.fixture()
def tools():
    return build_local_tools(porkbun_enabled=True, desec_enabled=True, dokploy_enabled=True)


class TestLocalToolsRegistry:
    def test_registry_has_all_expected_tools(self, tools) -> None:
        names = {t.name for t in tools}
        expected = {
            "porkbun_list_domains",
            "porkbun_retrieve_records",
            "porkbun_create_record",
            "porkbun_update_record",
            "porkbun_delete_record",
            "porkbun_delete_record_by_name_type",
            "desec_list_domains",
            "desec_retrieve_records",
            "desec_create_record",
            "desec_update_record",
            "desec_delete_record",
            "dokploy_list_projects",
            "dokploy_get_project",
            "dokploy_get_application",
            "dokploy_get_compose",
            "dokploy_get_postgres",
            "dokploy_get_mysql",
            "dokploy_get_mongo",
            "dokploy_get_mariadb",
            "dokploy_get_redis",
        }
        assert expected == names

    def test_disabled_returns_empty(self) -> None:
        tools = build_local_tools(porkbun_enabled=False, desec_enabled=False, dokploy_enabled=False)
        assert tools == []

    def test_only_porkbun(self) -> None:
        tools = build_local_tools(porkbun_enabled=True, desec_enabled=False, dokploy_enabled=False)
        names = {t.name for t in tools}
        assert all(n.startswith("porkbun_") for n in names)
        assert len(tools) == 6

    def test_only_desec(self) -> None:
        tools = build_local_tools(porkbun_enabled=False, desec_enabled=True, dokploy_enabled=False)
        names = {t.name for t in tools}
        assert all(n.startswith("desec_") for n in names)
        assert len(tools) == 5

    def test_only_dokploy(self) -> None:
        tools = build_local_tools(porkbun_enabled=False, desec_enabled=False, dokploy_enabled=True)
        names = {t.name for t in tools}
        assert all(n.startswith("dokploy_") for n in names)
        assert len(tools) == 9


class TestPorkbunToolSchemas:
    def test_list_domains_has_no_required(self, tools) -> None:
        tool = _get_tool(tools, "porkbun_list_domains")
        assert tool.input_schema.get("required", []) == []

    def test_retrieve_records_requires_domain(self, tools) -> None:
        tool = _get_tool(tools, "porkbun_retrieve_records")
        assert "domain" in tool.input_schema["required"]

    def test_create_record_requires_domain_type_name_content(self, tools) -> None:
        tool = _get_tool(tools, "porkbun_create_record")
        required = tool.input_schema["required"]
        assert "domain" in required
        assert "type" in required
        assert "name" in required
        assert "content" in required

    def test_update_record_requires_domain_record_id(self, tools) -> None:
        tool = _get_tool(tools, "porkbun_update_record")
        required = tool.input_schema["required"]
        assert "domain" in required
        assert "record_id" in required

    def test_delete_record_requires_domain_record_id(self, tools) -> None:
        tool = _get_tool(tools, "porkbun_delete_record")
        required = tool.input_schema["required"]
        assert "domain" in required
        assert "record_id" in required

    def test_delete_by_name_type_requires_domain_type(self, tools) -> None:
        tool = _get_tool(tools, "porkbun_delete_record_by_name_type")
        required = tool.input_schema["required"]
        assert "domain" in required
        assert "type" in required


class TestDeSecToolSchemas:
    def test_list_domains_has_no_required(self, tools) -> None:
        tool = _get_tool(tools, "desec_list_domains")
        assert tool.input_schema.get("required", []) == []

    def test_retrieve_records_requires_domain(self, tools) -> None:
        tool = _get_tool(tools, "desec_retrieve_records")
        assert "domain" in tool.input_schema["required"]

    def test_create_record_requires_domain_type_records(self, tools) -> None:
        tool = _get_tool(tools, "desec_create_record")
        required = tool.input_schema["required"]
        assert "domain" in required
        assert "type" in required
        assert "records" in required

    def test_update_record_requires_domain_subname_type_records(self, tools) -> None:
        tool = _get_tool(tools, "desec_update_record")
        required = tool.input_schema["required"]
        assert "domain" in required
        assert "subname" in required
        assert "type" in required
        assert "records" in required

    def test_delete_record_requires_domain_subname_type(self, tools) -> None:
        tool = _get_tool(tools, "desec_delete_record")
        required = tool.input_schema["required"]
        assert "domain" in required
        assert "subname" in required
        assert "type" in required


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


class TestAPIErrors:
    def test_porkbun_error_attributes(self) -> None:
        exc = PorkbunAPIError(status="ERROR", message="not found")
        assert exc.status == "ERROR"
        assert exc.message == "not found"
        assert "not found" in str(exc)

    def test_desec_error_attributes(self) -> None:
        exc = DeSecAPIError(status=404, message="not found")
        assert exc.status == 404
        assert exc.message == "not found"
        assert "404" in str(exc)

    def test_dokploy_error_attributes(self) -> None:
        exc = DokployAPIError(status=403, message="forbidden")
        assert exc.status == 403
        assert exc.message == "forbidden"
        assert "403" in str(exc)
