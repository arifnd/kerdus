from __future__ import annotations

import pytest

from app.tools import build_local_tools
from app.tools.porkbun import PorkbunAPIError


def _get_tool(tools, name):
    return next(t for t in tools if t.name == name)


@pytest.fixture()
def tools():
    return build_local_tools(enabled=True)


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
        }
        assert expected == names

    def test_disabled_returns_empty(self) -> None:
        tools = build_local_tools(enabled=False)
        assert tools == []


class TestToolSchemas:
    def test_list_domains_has_no_required(self, tools) -> None:
        tool = _get_tool(tools, "porkbun_list_domains")
        assert tool.input_schema["required"] == []

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


class TestPorkbunAPIError:
    def test_error_attributes(self) -> None:
        exc = PorkbunAPIError(status="ERROR", message="not found")
        assert exc.status == "ERROR"
        assert exc.message == "not found"
        assert "not found" in str(exc)
