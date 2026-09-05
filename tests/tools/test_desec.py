from __future__ import annotations

from app.tools.desec.render import render_domains, render_records


def _get_tool(tools, name):
    return next(t for t in tools if t.name == name)


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


class TestDeSecRender:
    def test_render_domains(self) -> None:
        domains = [{"name": "example.com"}, {"name": "dedyn.io"}]
        assert render_domains(domains) == (
            "<code>example.com</code>\n<code>dedyn.io</code>"
        )

    def test_render_domains_empty(self) -> None:
        assert render_domains([]) == "No domains found."

    def test_render_records(self) -> None:
        rrsets = [
            {"type": "A", "subname": "www", "records": ["1.2.3.4", "5.6.7.8"], "ttl": 3600},
            {"type": "A", "subname": "", "records": ["9.9.9.9"]},
        ]
        assert render_records(rrsets) == (
            '<code>A www</code> -> 1.2.3.4, 5.6.7.8 (ttl=3600)\n'
            '<code>A @</code> -> 9.9.9.9'
        )

    def test_render_records_empty(self) -> None:
        assert render_records([]) == "No DNS records found."