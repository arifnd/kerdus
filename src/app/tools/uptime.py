from __future__ import annotations

import time
from typing import Any

import httpx

from ..logging import get_logger

log = get_logger("tools.uptime")

DEFAULT_TIMEOUT = 10.0

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True)
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        finally:
            _client = None


async def check_uptime(url: str) -> dict[str, Any]:
    """Run a single HTTP uptime check against ``url``.

    Returns a dict with ``url``, ``up``, ``status_code``, ``latency_ms`` and
    optionally ``error``. A URL is considered UP for HTTP 2xx/3xx responses;
    anything else (4xx/5xx, timeout, connection error) is DOWN.
    """
    start = time.monotonic()
    try:
        response = await get_client().get(url)
        latency_ms = round((time.monotonic() - start) * 1000)
        up = response.is_success or response.status_code in (300, 301, 302, 303, 307, 308)
        return {
            "url": url,
            "up": up,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
        }
    except httpx.TimeoutException:
        latency_ms = round((time.monotonic() - start) * 1000)
        return {
            "url": url,
            "up": False,
            "status_code": None,
            "latency_ms": latency_ms,
            "error": f"Request timed out after {DEFAULT_TIMEOUT}s",
        }
    except httpx.HTTPError as exc:
        latency_ms = round((time.monotonic() - start) * 1000)
        return {
            "url": url,
            "up": False,
            "status_code": None,
            "latency_ms": latency_ms,
            "error": f"Connection error: {exc.__class__.__name__}",
        }
    except Exception as exc:  # noqa: BLE001 - never raise during a check
        latency_ms = round((time.monotonic() - start) * 1000)
        return {
            "url": url,
            "up": False,
            "status_code": None,
            "latency_ms": latency_ms,
            "error": f"Unexpected error: {exc.__class__.__name__}",
        }