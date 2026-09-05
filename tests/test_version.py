from __future__ import annotations

from app.version import _VERSION_PATTERN, get_version


def test_get_version_is_known() -> None:
    version = get_version()
    assert version != "unknown"
    assert version.count(".") >= 1


def test_pyproject_version_regex() -> None:
    match = _VERSION_PATTERN.search('version = "0.1.0"')
    assert match is not None
    assert match.group(1) == "0.1.0"