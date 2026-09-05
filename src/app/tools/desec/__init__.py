from __future__ import annotations

from ..base import LocalTool
from .api import (
    DeSecAPIError,
    create_record,
    delete_record,
    list_domains,
    retrieve_records,
    update_record,
)

__all__ = [
    "DeSecAPIError",
    "build_desec_tools",
    "create_record",
    "delete_record",
    "list_domains",
    "retrieve_records",
    "update_record",
]


def build_desec_tools() -> list[LocalTool]:
    return [
        LocalTool(
            name="desec_list_domains",
            description="List all domains in the deSEC account.",
            input_schema={"type": "object", "properties": {}},
            func=list_domains,
        ),
        LocalTool(
            name="desec_retrieve_records",
            description="Retrieve all DNS records (RRsets) for a domain.",
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
            name="desec_create_record",
            description="Create a new DNS record (RRset) for a domain.",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The domain name (e.g. example.com)",
                    },
                    "subname": {
                        "type": "string",
                        "description": "Subdomain portion (e.g. 'www'). Use '@' or '' for apex.",
                    },
                    "type": {
                        "type": "string",
                        "description": "DNS record type (A, AAAA, CNAME, MX, TXT, SRV, CAA, etc.)",
                    },
                    "records": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of record content strings (e.g. ['1.2.3.4']).",
                    },
                    "ttl": {
                        "type": "integer",
                        "description": "Time to live in seconds (default: 3600).",
                        "default": 3600,
                    },
                },
                "required": ["domain", "type", "records"],
            },
            func=create_record,
        ),
        LocalTool(
            name="desec_update_record",
            description="Update an existing DNS record (RRset) by subname and type.",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The domain name (e.g. example.com)",
                    },
                    "subname": {
                        "type": "string",
                        "description": "Subdomain portion. Use '@' or '' for apex.",
                    },
                    "type": {
                        "type": "string",
                        "description": "DNS record type.",
                    },
                    "records": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of record content strings.",
                    },
                    "ttl": {
                        "type": "integer",
                        "description": "Time to live in seconds (default: 3600).",
                        "default": 3600,
                    },
                },
                "required": ["domain", "subname", "type", "records"],
            },
            func=update_record,
        ),
        LocalTool(
            name="desec_delete_record",
            description="Delete a DNS record (RRset) by subname and type.",
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The domain name (e.g. example.com)",
                    },
                    "subname": {
                        "type": "string",
                        "description": "Subdomain portion. Use '@' or '' for apex.",
                    },
                    "type": {
                        "type": "string",
                        "description": "DNS record type.",
                    },
                },
                "required": ["domain", "subname", "type"],
            },
            func=delete_record,
        ),
    ]