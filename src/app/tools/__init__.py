from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import desec, dokploy, porkbun


class ToolDisabledError(Exception):
    pass


@dataclass(frozen=True)
class LocalTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    func: Any


def build_local_tools(
    porkbun_enabled: bool = True,
    desec_enabled: bool = True,
    dokploy_enabled: bool = True,
) -> list[LocalTool]:
    tools: list[LocalTool] = []

    if porkbun_enabled:
        tools.extend(_porkbun_tools())

    if desec_enabled:
        tools.extend(_desec_tools())

    if dokploy_enabled:
        tools.extend(_dokploy_tools())

    return tools


def _porkbun_tools() -> list[LocalTool]:
    return [
        LocalTool(
            name="porkbun_list_domains",
            description=(
                "List domains in the Porkbun account. By default only domains with API access "
                "enabled (status Active) are returned; set include_all to true to list all domains."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "include_all": {
                        "type": "boolean",
                        "description": (
                            "Set to true to include all domains, including those without API "
                            "access enabled."
                        ),
                        "default": False,
                    }
                },
            },
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


def _desec_tools() -> list[LocalTool]:
    return [
        LocalTool(
            name="desec_list_domains",
            description="List all domains in the deSEC account.",
            input_schema={"type": "object", "properties": {}},
            func=desec.list_domains,
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
            func=desec.retrieve_records,
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
            func=desec.create_record,
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
            func=desec.update_record,
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
            func=desec.delete_record,
        ),
    ]


def _dokploy_tools() -> list[LocalTool]:
    return [
        LocalTool(
            name="dokploy_list_projects",
            description="List all projects with their apps, databases, and compose services.",
            input_schema={"type": "object", "properties": {}},
            func=dokploy.list_projects,
        ),
        LocalTool(
            name="dokploy_get_project",
            description="Get project details including all apps, databases, and compose services.",
            input_schema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "The project ID.",
                    }
                },
                "required": ["project_id"],
            },
            func=dokploy.get_project,
        ),
        LocalTool(
            name="dokploy_get_application",
            description="Get application details (source, build config, status, domains, etc.).",
            input_schema={
                "type": "object",
                "properties": {
                    "application_id": {
                        "type": "string",
                        "description": "The application ID.",
                    }
                },
                "required": ["application_id"],
            },
            func=dokploy.get_application,
        ),
        LocalTool(
            name="dokploy_get_compose",
            description="Get compose service details (docker-compose config, status, etc.).",
            input_schema={
                "type": "object",
                "properties": {
                    "compose_id": {
                        "type": "string",
                        "description": "The compose service ID.",
                    }
                },
                "required": ["compose_id"],
            },
            func=dokploy.get_compose,
        ),
        LocalTool(
            name="dokploy_get_postgres",
            description="Get PostgreSQL database details.",
            input_schema={
                "type": "object",
                "properties": {
                    "postgres_id": {
                        "type": "string",
                        "description": "The PostgreSQL database ID.",
                    }
                },
                "required": ["postgres_id"],
            },
            func=dokploy.get_postgres,
        ),
        LocalTool(
            name="dokploy_get_mysql",
            description="Get MySQL database details.",
            input_schema={
                "type": "object",
                "properties": {
                    "mysql_id": {
                        "type": "string",
                        "description": "The MySQL database ID.",
                    }
                },
                "required": ["mysql_id"],
            },
            func=dokploy.get_mysql,
        ),
        LocalTool(
            name="dokploy_get_mongo",
            description="Get MongoDB database details.",
            input_schema={
                "type": "object",
                "properties": {
                    "mongo_id": {
                        "type": "string",
                        "description": "The MongoDB database ID.",
                    }
                },
                "required": ["mongo_id"],
            },
            func=dokploy.get_mongo,
        ),
        LocalTool(
            name="dokploy_get_mariadb",
            description="Get MariaDB database details.",
            input_schema={
                "type": "object",
                "properties": {
                    "mariadb_id": {
                        "type": "string",
                        "description": "The MariaDB database ID.",
                    }
                },
                "required": ["mariadb_id"],
            },
            func=dokploy.get_mariadb,
        ),
        LocalTool(
            name="dokploy_get_redis",
            description="Get Redis database details.",
            input_schema={
                "type": "object",
                "properties": {
                    "redis_id": {
                        "type": "string",
                        "description": "The Redis database ID.",
                    }
                },
                "required": ["redis_id"],
            },
            func=dokploy.get_redis,
        ),
    ]
