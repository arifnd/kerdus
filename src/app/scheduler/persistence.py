from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ..logging import get_logger

log = get_logger("scheduler.jobs")


def load_schedules(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        jobs = data.get("jobs", [])
        if not isinstance(jobs, list):
            log.warning("schedules file {} has non-list jobs; ignoring", path)
            return []
        return [j for j in jobs if isinstance(j, dict)]
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("failed to read schedules file {}: {}; starting empty", path, exc)
        return []


def save_schedules(path: str | Path, jobs: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"jobs": jobs}
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".schedules-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
