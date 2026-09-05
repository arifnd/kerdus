from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

_TEMPLATE_DIR = Path(__file__).parent
_ENV = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
    trim_blocks=True,
)


def _render(template: str, **context: Any) -> str:
    return _ENV.get_template(template).render(**context).strip()


def _domain_names(domains: list[Any]) -> list[str]:
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
    return names


def render_domains(result: dict[str, Any]) -> str:
    return _render("domains.html", domains=_domain_names(result.get("domains", [])))


def _record_content(record: dict[str, Any]) -> str:
    content = record.get("content")
    if content is None:
        content = record.get("records", [])
    if isinstance(content, list):
        return ", ".join(str(item) for item in content)
    return str(content)


def _record_values(record: dict[str, Any]) -> list[str]:
    content = record.get("content")
    if content is None:
        content = record.get("records", [])
    if isinstance(content, list):
        return [str(item) for item in content]
    return [str(content)]


def _record_suffix(record: dict[str, Any]) -> str:
    parts: list[str] = []
    if record.get("ttl") not in (None, ""):
        parts.append(f"ttl={record['ttl']}")
    return f" ({', '.join(parts)})" if parts else ""


def render_records(result: dict[str, Any]) -> str:
    domain = str(result.get("domain") or "")
    groups: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, str, str]] = set()
    for record in result.get("records", []):
        if not isinstance(record, dict):
            continue
        name = str(record.get("name") or record.get("subname") or "@")
        record_type = str(record.get("type", ""))
        content = _record_content(record)
        key = (name, record_type, content)
        if key in seen:
            continue
        seen.add(key)
        groups.setdefault(record_type, []).append(
            {
                "name": name,
                "content": content,
                "values": _record_values(record),
                "suffix": _record_suffix(record),
            }
        )
    rows = [{"type": t, "records": records} for t, records in groups.items()]
    body = _render("records.html", domain=domain, groups=rows)
    cloudflare = result.get("cloudflare")
    if isinstance(cloudflare, str) and cloudflare.lower() in {"1", "true", "yes"}:
        body = "This domain uses Cloudflare, so only some records are editable here.\n\n" + body
    return body
