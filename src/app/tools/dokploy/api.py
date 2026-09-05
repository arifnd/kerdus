from __future__ import annotations

from typing import Any

import httpx

from ...logging import get_logger
from ...settings import get_settings

log = get_logger("tools.dokploy")


class DokployAPIError(Exception):
    def __init__(self, status: int, message: str = "") -> None:
        self.status = status
        self.message = message
        super().__init__(f"Dokploy API error {status}: {message}")


def _headers() -> dict[str, str]:
    s = get_settings()
    return {
        "x-api-key": s.dokploy_api_key,
        "accept": "application/json",
    }


def _base_url() -> str:
    s = get_settings()
    url = s.dokploy_url.rstrip("/")
    return f"{url}/api"


async def _get(path: str, params: dict[str, str] | None = None) -> Any:
    url = f"{_base_url()}/{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers=_headers(), params=params)
        if resp.status_code >= 400:
            detail = ""
            try:
                data = resp.json()
                detail = data.get("message", str(data))
            except Exception:  # noqa: BLE001
                detail = resp.text
            raise DokployAPIError(status=resp.status_code, message=detail)
        return resp.json()


async def _post(path: str, body: dict[str, Any] | None = None) -> Any:
    url = f"{_base_url()}/{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=_headers(), json=body or {})
        if resp.status_code >= 400:
            detail = ""
            try:
                data = resp.json()
                detail = data.get("message", str(data))
            except Exception:  # noqa: BLE001
                detail = resp.text
            raise DokployAPIError(status=resp.status_code, message=detail)
        return resp.json()


_SECRET_MARKERS = ("apikey", "password", "token", "secret", "_key")
_ENV_KEYS = frozenset(
    {
        "env",
        "buildargs",
        "buildsecrets",
        "previewenv",
        "previewbuildargs",
        "previewbuildsecrets",
    }
)


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in _ENV_KEYS or any(marker in lowered for marker in _SECRET_MARKERS)


def _strip_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_secrets(v) for k, v in value.items() if not _is_secret_key(k)}
    if isinstance(value, list):
        return [_strip_secrets(item) for item in value]
    return value


def _sanitized(data: Any) -> Any:
    if get_settings().dokploy_show_secret:
        return data
    return _strip_secrets(data)


async def list_projects() -> list[Any]:
    return _sanitized(await _get("project.all"))


async def get_project(project_id: str) -> dict[str, Any]:
    return _sanitized(await _get("project.one", params={"projectId": project_id}))


async def get_application(application_id: str) -> dict[str, Any]:
    return _sanitized(await _get("application.one", params={"applicationId": application_id}))


async def get_compose(compose_id: str) -> dict[str, Any]:
    return _sanitized(await _get("compose.one", params={"composeId": compose_id}))


async def get_postgres(postgres_id: str) -> dict[str, Any]:
    return _sanitized(await _get("postgres.one", params={"postgresId": postgres_id}))


async def get_mysql(mysql_id: str) -> dict[str, Any]:
    return _sanitized(await _get("mysql.one", params={"mysqlId": mysql_id}))


async def get_mongo(mongo_id: str) -> dict[str, Any]:
    return _sanitized(await _get("mongo.one", params={"mongoId": mongo_id}))


async def get_mariadb(mariadb_id: str) -> dict[str, Any]:
    return _sanitized(await _get("mariadb.one", params={"mariadbId": mariadb_id}))


async def get_redis(redis_id: str) -> dict[str, Any]:
    return _sanitized(await _get("redis.one", params={"redisId": redis_id}))
