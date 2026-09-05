from __future__ import annotations

from ..base import LocalTool
from .api import (
    PorkbunAPIError,
    create_record,
    delete_record,
    delete_record_by_name_type,
    list_domains,
    retrieve_records,
    update_record,
)

__all__ = [
    "PorkbunAPIError",
    "build_porkbun_tools",
    "create_record",
    "delete_record",
    "delete_record_by_name_type",
    "list_domains",
    "retrieve_records",
    "update_record",
]


def build_porkbun_tools() -> list[LocalTool]:
    return [
        LocalTool(
            name="porkbun_list_domains",
            description=(
                "List domains in the Porkbun account. By default only domains opted in to API "
                "access are returned. When the user asks for ALL domains, a complete list, or "
                "every domain they own, set include_all to true so all domains are returned."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "include_all": {
                        "type": "boolean",
                        "description": (
                            "Set to true when the user wants every domain in the account, including "
                            "those without API access enabled. Omit or false for API-enabled "
                            "domains only."
                        ),
                        "default": False,
                    }
                },
            },
            func=list_domains,
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
            func=retrieve_records,
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
            func=create_record,
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
            func=update_record,
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
            func=delete_record,
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
            func=delete_record_by_name_type,
        ),
    ]