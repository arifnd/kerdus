from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..logging import get_logger
from .jobs import StateTracker, StatusEvent, run_uptime_job
from .persistence import load_schedules, save_schedules

log = get_logger("scheduler")


StatusHandler = Callable[[StatusEvent], Awaitable[None]]


class SchedulerService:
    def __init__(self, state_path: str | Path = "data/schedules.json") -> None:
        self._state_path = Path(state_path)
        self._jobs: dict[str, dict[str, Any]] = {}
        self._tracker = StateTracker()
        self._scheduler = AsyncIOScheduler()
        self._handlers: list[StatusHandler] = []

    def add_status_handler(self, handler: StatusHandler) -> None:
        self._handlers.append(handler)

    async def _emit(self, event: StatusEvent) -> None:
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as exc:  # noqa: BLE001 - never let alerting break the loop
                log.warning("status handler error: {}", exc)

    async def _run_job(self, job: dict[str, Any]) -> None:
        try:
            event = await run_uptime_job(job, self._tracker)
            if event is not None:
                await self._emit(event)
        except Exception as exc:  # noqa: BLE001 - one job never breaks the scheduler
            log.error("uptime job {} failed: {}", job["id"], exc)

    def start(self) -> None:
        for job in self._jobs.values():
            self._schedule(job)
        self._scheduler.start()
        log.info("scheduler started with {} jobs", len(self._jobs))

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown()
        self.save_state()
        log.info("scheduler stopped")

    def is_running(self) -> bool:
        return bool(self._scheduler.running)

    def load_state(self) -> None:
        self._jobs = {}
        self._tracker.clear()
        for job in load_schedules(self._state_path):
            self._jobs[job["id"]] = job

    def save_state(self) -> None:
        save_schedules(self._state_path, list(self._jobs.values()))

    def _schedule(self, job: dict[str, Any]) -> None:
        if not job.get("enabled", True):
            return
        trigger = IntervalTrigger(seconds=int(job["interval_seconds"]))
        self._scheduler.add_job(
            self._run_job,
            trigger=trigger,
            args=[job],
            id=job["id"],
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def _reschedule_all(self) -> None:
        self._scheduler.remove_all_jobs()
        for job in self._jobs.values():
            self._schedule(job)

    async def create(self, job_id: str, url: str, interval_seconds: int) -> dict[str, Any]:
        return self._create(job_id, url, interval_seconds)

    def _create(self, job_id: str, url: str, interval_seconds: int) -> dict[str, Any]:
        if job_id in self._jobs:
            raise ValueError(f"job {job_id!r} already exists")
        job = {
            "id": job_id,
            "type": "uptime",
            "url": url,
            "interval_seconds": interval_seconds,
            "enabled": True,
        }
        self._jobs[job_id] = job
        self._schedule(job)
        self.save_state()
        return {"success": True, "job_id": job_id}

    async def remove(self, job_id: str) -> dict[str, Any]:
        return self._remove(job_id)

    def _remove(self, job_id: str) -> dict[str, Any]:
        if job_id not in self._jobs:
            raise ValueError(f"job {job_id!r} not found")
        del self._jobs[job_id]
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
        self.save_state()
        return {"success": True}

    async def pause(self, job_id: str) -> dict[str, Any]:
        return self._pause(job_id)

    def _pause(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"job {job_id!r} not found")
        job["enabled"] = False
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
        self.save_state()
        return {"success": True}

    async def resume(self, job_id: str) -> dict[str, Any]:
        return self._resume(job_id)

    def _resume(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job is None:
            raise ValueError(f"job {job_id!r} not found")
        job["enabled"] = True
        self._schedule(job)
        self.save_state()
        return {"success": True}

    async def list(self) -> list[dict[str, Any]]:
        return self._list()

    def _list(self) -> list[dict[str, Any]]:
        return [
            {
                "id": j["id"],
                "url": j["url"],
                "interval_seconds": j["interval_seconds"],
                "enabled": j["enabled"],
            }
            for j in self._jobs.values()
        ]
