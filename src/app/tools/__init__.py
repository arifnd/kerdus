from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import porkbun


class ToolDisabledError(Exception):
    pass


@dataclass(frozen=True)
class LocalTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    func: Any


def build_local_tools(enabled: bool = True) -> list[LocalTool]:
    if not enabled:
        return []

    return [
        LocalTool(
            name="porkbun_list_domains",
            description="List all domains in the Porkbun account that have API access enabled.",
            input_schema={"type": "object", "properties": {}},
            func=porkbun.list_domains,
        ),
        LocalTool(
            name="porkbun_retrieve_records",
            description="Retrieve all editable DNS records for a domain.",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The domain name (e.g. example.com)",
                    }
                },
                "required": ["domain"],
            },
            func=porkbun.retrieve_records,
        ),
        LocalTool(
            name="porkbun_create_record",
            description="Create a new DNS record for a domain.",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The domain name (e.g. example.com)",
                    },
                    "type": {
                        "type": "string",
                        "description": "DNS record type (A, AAAA, CNAME, MX, TXT, SRV, CAA, ALIAS, etc.)",
                    },
                    "name": {
                        "type": "string",
                        "description": "Subdomain portion (e.g. 'www' or '@' for root).",
                    },
                    "content": {
                        "type": "string",
                        "description": "Record content (e.g. IP address, hostname, text value).",
                    },
                    "ttl": {
                        "type": "string",
                        "description": "Time to live in seconds (default: 600).",
                        "default": "600",
                    },
                    "prio": {
                        "type": "string",
                        "description": "Priority for MX/SRV records (default: 0).",
                        "default": "0",
                    },
                },
                "required": ["domain", "type", "name", "content"],
            },
            func=porkbun.create_record,
        ),
        LocalTool(
            name="porkbun_update_record",
            description="Update an existing DNS record by its ID.",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The domain name (e.g. example.com)",
                    },
                    "record_id": {
                        "type": "string",
                        "description": "The numeric record ID (from retrieve_records).",
                    },
                    "type": {
                        "type": "string",
                        "description": "DNS record type.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Subdomain portion.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Record content.",
                    },
                    "ttl": {
                        "type": "string",
                        "description": "Time to live in seconds (default: 600).",
                        "default": "600",
                    },
                    "prio": {
                        "type": "string",
                        "description": "Priority for MX/SRV records (default: 0).",
                        "default": "0",
                    },
                },
                "required": ["domain", "record_id", "type", "name", "content"],
            },
            func=porkbun.update_record,
        ),
        LocalTool(
            name="porkbun_delete_record",
            description="Delete a DNS record by its ID.",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The domain name (e.g. example.com)",
                    },
                    "record_id": {
                        "type": "string",
                        "description": "The numeric record ID to delete.",
                    },
                },
                "required": ["domain", "record_id"],
            },
            func=porkbun.delete_record,
        ),
        LocalTool(
            name="porkbun_delete_record_by_name_type",
            description="Delete DNS records by subdomain and record type.",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The domain name (e.g. example.com)",
                    },
                    "type": {
                        "type": "string",
                        "description": "DNS record type (A, CNAME, TXT, etc.).",
                    },
                    "subdomain": {
                        "type": "string",
                        "description": "Subdomain portion. Omit or empty for root domain.",
                        "default": "",
                    },
                },
                "required": ["domain", "type"],
            },
            func=porkbun.delete_record_by_name_type,
        ),
    ]
