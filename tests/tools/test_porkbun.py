from __future__ import annotations

from app.tools.porkbun.render import render_domains, render_records


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
                "Set to true when the user wants every domain in the account, including those "
                "without API access enabled. Omit or false for API-enabled domains only."
            ),
            "default": False,
        }
        assert "status Active" not in tool.description
        assert "API" in tool.description

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


class TestPorkbunRender:
    def test_render_domains(self) -> None:
        result = {
            "domains": [
                {"domain": "example.com", "status": "ACTIVE"},
                {"domain": "example.org", "status": "ACTIVE"},
            ]
        }
        assert render_domains(result) == (
            "Here are the domains in your Porkbun account:\n• example.com\n• example.org"
        )

    def test_render_domains_skips_missing_name(self) -> None:
        assert render_domains({"domains": [{"status": "ACTIVE"}]}) == "No domains found."

    def test_render_domains_empty(self) -> None:
        assert render_domains({"domains": []}) == "No domains found."

    def test_render_records(self) -> None:
        result = {
            "domain": "example.com",
            "records": [
                {"type": "A", "name": "www", "content": "1.2.3.4", "ttl": "600"},
                {"type": "A", "name": "www", "content": "1.2.3.4", "ttl": "600"},
                {"type": "TXT", "name": "@", "content": "v=spf1"},
            ],
        }
        assert render_records(result) == (
            "Here are the DNS records for the domain example.com:\n"
            "• A www -> 1.2.3.4 (ttl=600)\n"
            "• TXT @ -> v=spf1"
        )

    def test_render_records_includes_id(self) -> None:
        result = {
            "domain": "example.com",
            "records": [
                {"type": "CNAME", "name": "api", "content": "foo.example.com", "id": "1234"}
            ],
        }
        assert render_records(result) == (
            "Here are the DNS records for the domain example.com:\n"
            "• CNAME api -> foo.example.com (id=1234)"
        )

    def test_render_records_empty(self) -> None:
        assert render_records({"domain": "example.com", "records": []}) == "No DNS records found."
