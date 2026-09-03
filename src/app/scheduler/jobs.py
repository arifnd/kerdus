from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..logging import get_logger
from ..tools.uptime import check_uptime

log = get_logger("scheduler.jobs")


@dataclass(frozen=True)
class StatusEvent:
    """Emitted when an uptime check changes state (UP<->DOWN)."""

    job_id: str
    url: str
    kind: str  # "up" or "down"
    result: dict[str, Any]


async def run_uptime_job(job: dict[str, Any], tracker: StateTracker) -> StatusEvent | None:
    """Run one uptime job and return a StatusEvent only if the state changed.

    The first-ever check always emits an event so the initial state is known.
    """
    url = job["url"]
    previous = tracker.get(job["id"])
    result = await check_uptime(url)

    current_kind = "up" if result["up"] else "down"
    if previous is None or previous != current_kind:
        tracker.set(job["id"], current_kind)
        log.info("uptime state change for {}: {} -> {} ({})", job["id"], previous, current_kind, result.get("status_code"))
        return StatusEvent(
            job_id=job["id"],
            url=url,
            kind=current_kind,
            result=result,
        )
    return None


class StateTracker:
    """In-memory map of job_id -> last known state ("up"/"down")."""

    def __init__(self) -> None:
        self._states: dict[str, str] = {}

    def get(self, job_id: str) -> str | None:
        return self._states.get(job_id)

    def set(self, job_id: str, state: str) -> None:
        self._states[job_id] = state

    def clear(self) -> None:
        self._states.clear()
