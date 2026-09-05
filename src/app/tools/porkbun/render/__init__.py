from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = Path(__file__).parent
_ENV = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=True)


def _render(template: str, **context: Any) -> str:
    return _ENV.get_template(template).render(**context).strip()


def render_domains(domains: list[Any]) -> str:
    names: list[str] = []
    for domain in domains:
        if isinstance(domain, str):
            names.append(domain)
            continue
        if not isinstance(domain, dict):
            continue
        name = domain.get("domain") or domain.get("name")
        if name:
            names.append(str(name))
    return _render("domains.html", domains=names)


def _record_content(record: dict[str, Any]) -> str:
    content = record.get("content")
    if content is None:
        content = record.get("records", [])
    if isinstance(content, list):
        return ", ".join(str(item) for item in content)
    return str(content)


def render_records(records: list[Any]) -> str:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        name = str(record.get("name") or record.get("subname") or "@")
        record_type = str(record.get("type", ""))
        content = _record_content(record)
        key = (name, record_type, content)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "type": record_type,
                "name": name,
                "content": content,
                "id": record.get("id"),
                "ttl": record.get("ttl"),
            }
        )
    return _render("records.html", records=rows)