from __future__ import annotations

from typing import Any

from ..logging import get_logger

log = get_logger("tools.scheduler")


class MemorySchedulerService:
    """Minimal in-memory scheduler backend used during development and tests.

    The real APScheduler-backed service will implement SchedulerBackend and
    supersede this once Task 04 is built.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    async def create(
        self, job_id: str, url: str, interval_seconds: int
    ) -> dict[str, Any]:
        if job_id in self._jobs:
            raise ValueError(f"job {job_id!r} already exists")
        self._jobs[job_id] = {
            "id": job_id,
            "url": url,
            "interval_seconds": interval_seconds,
            "enabled": True,
        }
        return {"success": True, "job_id": job_id}

    async def remove(self, job_id: str) -> dict[str, Any]:
        if job_id not in self._jobs:
            raise ValueError(f"job {job_id!r} not found")
        del self._jobs[job_id]
        return {"success": True}

    async def pause(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"job {job_id!r} not found")
        job["enabled"] = False
        return {"success": True}

    async def resume(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"job {job_id!r} not found")
        job["enabled"] = True
        return {"success": True}

    async def list(self) -> list[dict[str, Any]]:
        return [
            {
                "id": j["id"],
                "url": j["url"],
                "interval_seconds": j["interval_seconds"],
                "enabled": j["enabled"],
            }
            for j in self._jobs.values()
        ]