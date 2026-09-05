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
        name = domain.get("name") or domain.get("domain")
        if name:
            names.append(str(name))
    return _render("domains.html", domains=names)


def render_records(rrsets: list[Any]) -> str:
    rows: list[dict[str, Any]] = []
    for rrset in rrsets:
        if not isinstance(rrset, dict):
            continue
        subname = str(rrset.get("subname") or "@")
        record_type = str(rrset.get("type", ""))
        content = ", ".join(str(item) for item in rrset.get("records", []))
        rows.append(
            {
                "type": record_type,
                "name": subname,
                "content": content,
                "ttl": rrset.get("ttl"),
            }
        )
    return _render("records.html", records=rows)