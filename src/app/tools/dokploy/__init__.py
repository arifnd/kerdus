from __future__ import annotations

from ..base import LocalTool
from .api import (
    DokployAPIError,
    get_application,
    get_compose,
    get_mariadb,
    get_mongo,
    get_mysql,
    get_postgres,
    get_project,
    get_redis,
    list_projects,
)

__all__ = [
    "DokployAPIError",
    "build_dokploy_tools",
    "get_application",
    "get_compose",
    "get_mariadb",
    "get_mongo",
    "get_mysql",
    "get_postgres",
    "get_project",
    "get_redis",
    "list_projects",
]


def build_dokploy_tools() -> list[LocalTool]:
    return [
        LocalTool(
            name="dokploy_list_projects",
            description="List all projects with their apps, databases, and compose services.",
            input_schema={"type": "object", "properties": {}},
            func=list_projects,
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
            func=get_project,
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
            func=get_application,
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
            func=get_compose,
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
            func=get_postgres,
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
            func=get_mysql,
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
            func=get_mongo,
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
            func=get_mariadb,
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
            func=get_redis,
        ),
    ]