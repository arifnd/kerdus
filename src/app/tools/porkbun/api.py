from __future__ import annotations

from typing import Any

import httpx

from ...logging import get_logger
from ...settings import get_settings

log = get_logger("tools.porkbun")

BASE_URL = "https://api.porkbun.com/api/json/v3"


class PorkbunAPIError(Exception):
    def __init__(self, status: str, message: str = "") -> None:
        self.status = status
        self.message = message
        super().__init__(f"Porkbun API error: {status} — {message}")


def _headers() -> dict[str, str]:
    s = get_settings()
    return {
        "X-API-Key": s.porkbun_api_key,
        "X-Secret-API-Key": s.porkbun_secret_key,
        "Content-Type": "application/json",
    }


async def _post(path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{BASE_URL}/{path}"
    payload = body or {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=_headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()
    if data.get("status") != "SUCCESS":
        raise PorkbunAPIError(
            status=data.get("status", "UNKNOWN"),
            message=data.get("message", ""),
        )
    return data


async def list_domains(include_all: bool = False) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if not include_all:
        body["apiAccess"] = "yes"
    data = await _post("domain/listAll", body)
    return {"domains": data.get("domains", [])}


async def retrieve_records(domain: str) -> dict[str, Any]:
    data = await _post(f"dns/retrieve/{domain}")
    return {
        "cloudflare": data.get("cloudflare", "unknown"),
        "records": data.get("records", []),
    }


async def create_record(
    domain: str,
    type: str,
    name: str,
    content: str,
    ttl: str = "600",
    prio: str = "0",
) -> dict[str, Any]:
    body: dict[str, Any] = {"type": type, "name": name, "content": content, "ttl": ttl}
    if prio and prio != "0":
        body["prio"] = prio
    data = await _post(f"dns/create/{domain}", body)
    return {"id": data.get("id"), "status": data.get("status")}


async def update_record(
    domain: str,
    record_id: str,
    type: str,
    name: str,
    content: str,
    ttl: str = "600",
    prio: str = "0",
) -> dict[str, Any]:
    body: dict[str, Any] = {"type": type, "name": name, "content": content, "ttl": ttl}
    if prio and prio != "0":
        body["prio"] = prio
    data = await _post(f"dns/update/{domain}/{record_id}", body)
    return {"status": data.get("status")}


async def delete_record(domain: str, record_id: str) -> dict[str, Any]:
    data = await _post(f"dns/delete/{domain}/{record_id}")
    return {"status": data.get("status")}


async def delete_record_by_name_type(domain: str, type: str, subdomain: str = "") -> dict[str, Any]:
    path = f"dns/deleteByNameType/{domain}/{type}"
    if subdomain:
        path += f"/{subdomain}"
    data = await _post(path)
    return {"status": data.get("status")}