from __future__ import annotations

from typing import Any

import httpx

from ...logging import get_logger
from ...settings import get_settings
from .render import render_domains, render_records

log = get_logger("tools.desec")

BASE_URL = "https://desec.io/api/v1"


class DeSecAPIError(Exception):
    def __init__(self, status: int, message: str = "") -> None:
        self.status = status
        self.message = message
        super().__init__(f"deSEC API error {status}: {message}")


def _headers() -> dict[str, str]:
    s = get_settings()
    return {
        "Authorization": f"Token {s.desec_token}",
        "Content-Type": "application/json",
    }


async def _request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    url = f"{BASE_URL}/{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(method, url, headers=_headers(), json=body if body else None)
        if resp.status_code == 204:
            return {"status": "deleted"}
        if resp.status_code >= 400:
            detail = ""
            try:
                data = resp.json()
                detail = str(data)
            except Exception:  # noqa: BLE001
                detail = resp.text
            raise DeSecAPIError(status=resp.status_code, message=detail)
        return resp.json()


async def list_domains() -> str:
    data = await _request("GET", "domains/")
    return render_domains(data)


async def retrieve_records(domain: str) -> str:
    data = await _request("GET", f"domains/{domain}/rrsets/")
    return render_records(data)


async def create_record(
    domain: str,
    subname: str,
    type: str,
    records: list[str],
    ttl: int = 3600,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "subname": subname,
        "type": type,
        "records": records,
        "ttl": ttl,
    }
    return await _request("POST", f"domains/{domain}/rrsets/", body)


async def update_record(
    domain: str,
    subname: str,
    type: str,
    records: list[str],
    ttl: int = 3600,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "subname": subname,
        "type": type,
        "records": records,
        "ttl": ttl,
    }
    return await _request("PUT", f"domains/{domain}/rrsets/{subname}/{type}/", body)


async def delete_record(domain: str, subname: str, type: str) -> dict[str, Any]:
    return await _request("DELETE", f"domains/{domain}/rrsets/{subname}/{type}/")