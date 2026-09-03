from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import scheduler_tools, uptime
from .scheduler_tools import SchedulerBackend


@dataclass(frozen=True)
class LocalTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    func: Any


def build_local_tools(scheduler: SchedulerBackend) -> list[LocalTool]:
    """Build the full registry of safe local tools bound to *scheduler*."""
    return [
        LocalTool(
            name="check_uptime",
            description=(
                "Run a single HTTP uptime check against a URL. "
                "Returns status code, latency, and whether the endpoint is UP."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to check",
                    }
                },
                "required": ["url"],
            },
            func=uptime.check_uptime,
        ),
        LocalTool(
            name="create_uptime_check",
            description="Create a recurring uptime check with a given interval.",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "A unique identifier for the check (letters, digits, _ or -)",
                    },
                    "url": {
                        "type": "string",
                        "description": "The URL to monitor",
                    },
                    "interval_seconds": {
                        "type": "integer",
                        "description": "How often to check in seconds (min 30, max 86400)",
                    },
                },
                "required": ["id", "url", "interval_seconds"],
            },
            func=scheduler_tools.make_create(scheduler),
        ),
        LocalTool(
            name="list_scheduled_checks",
            description="List all configured uptime monitoring jobs.",
            input_schema={"type": "object", "properties": {}},
            func=scheduler_tools.make_list(scheduler),
        ),
        LocalTool(
            name="remove_scheduled_check",
            description="Remove an uptime monitoring job.",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The job id to remove",
                    }
                },
                "required": ["id"],
            },
            func=scheduler_tools.make_remove(scheduler),
        ),
        LocalTool(
            name="pause_scheduled_check",
            description="Pause an uptime monitoring job.",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The job id to pause",
                    }
                },
                "required": ["id"],
            },
            func=scheduler_tools.make_pause(scheduler),
        ),
        LocalTool(
            name="resume_scheduled_check",
            description="Resume a paused uptime monitoring job.",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The job id to resume",
                    }
                },
                "required": ["id"],
            },
            func=scheduler_tools.make_resume(scheduler),
        ),
    ]