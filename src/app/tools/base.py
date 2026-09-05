from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ToolDisabledError(Exception):
    pass


@dataclass(frozen=True)
class LocalTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    func: Any