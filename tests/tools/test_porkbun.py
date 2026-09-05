from __future__ import annotations


def _get_tool(tools, name):
    return next(t for t in tools if t.name == name)


class TestPorkbunToolSchemas:
    def test_list_domains_has_no_required(self, tools) -> None:
        tool = _get_tool(tools, "porkbun_list_domains")
        assert tool.input_schema.get("required", []) == []
        assert "include_all" in tool.input_schema["properties"]
        assert tool.input_schema["properties"]["include_all"] == {
            "type": "boolean",
            "description": (
                "Set to true to include all domains, including those without API access enabled."
            ),
            "default": False,
        }

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