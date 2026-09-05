from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_VERSION_PATTERN = re.compile(r'^version\s*=\s*["\']?([^"\']+)', re.MULTILINE)


def _from_pyproject() -> str:
    path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    match = _VERSION_PATTERN.search(text)
    return match.group(1) if match else "unknown"


def get_version() -> str:
    try:
        return version("kerdus")
    except PackageNotFoundError:
        return _from_pyproject()