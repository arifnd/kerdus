from __future__ import annotations

import re
from typing import Any, Protocol, runtime_checkable

from ..logging import get_logger

log = get_logger("tools.scheduler")

_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MIN_INTERVAL = 30
MAX_INTERVAL = 86400


class InputError(ValueError):
    pass


@runtime_checkable
class SchedulerBackend(Protocol):
    async def create(
        self, job_id: str, url: str, interval_seconds: int
    ) -> dict[str, Any]: ...
    async def remove(self, job_id: str) -> dict[str, Any]: ...
    async def pause(self, job_id: str) -> dict[str, Any]: ...
    async def resume(self, job_id: str) -> dict[str, Any]: ...
    async def list(self) -> list[dict[str, Any]]: ...


def _validate_id(job_id: str) -> str:
    if not _ID_PATTERN.fullmatch(job_id):
        raise InputError(
            f"invalid id {job_id!r}: only letters, digits, '_' and '-' (1-64 chars) allowed"
        )
    return job_id


def _validate_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        raise InputError("url must start with http:// or https://")
    return url


def _validate_interval(interval_seconds: int) -> int:
    if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, int):
        raise InputError("interval_seconds must be an integer")
    if not (MIN_INTERVAL <= interval_seconds <= MAX_INTERVAL):
        raise InputError(
            f"interval_seconds must be between {MIN_INTERVAL} and {MAX_INTERVAL}"
        )
    return interval_seconds


def make_create(backend: SchedulerBackend):
    async def create_uptime_check(
        id: str, url: str, interval_seconds: int
    ) -> dict[str, Any]:
        job_id = _validate_id(id)
        _validate_url(url)
        _validate_interval(interval_seconds)
        return await backend.create(job_id, url, interval_seconds)

    return create_uptime_check


def make_list(backend: SchedulerBackend):
    async def list_scheduled_checks() -> list[dict[str, Any]]:
        return await backend.list()

    return list_scheduled_checks


def make_remove(backend: SchedulerBackend):
    async def remove_scheduled_check(id: str) -> dict[str, Any]:
        job_id = _validate_id(id)
        return await backend.remove(job_id)

    return remove_scheduled_check


def make_pause(backend: SchedulerBackend):
    async def pause_scheduled_check(id: str) -> dict[str, Any]:
        job_id = _validate_id(id)
        return await backend.pause(job_id)

    return pause_scheduled_check


def make_resume(backend: SchedulerBackend):
    async def resume_scheduled_check(id: str) -> dict[str, Any]:
        job_id = _validate_id(id)
        return await backend.resume(job_id)

    return resume_scheduled_check