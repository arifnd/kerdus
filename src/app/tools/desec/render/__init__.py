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
        name = domain.get("name") or domain.get("domain")
        if name:
            names.append(str(name))
    return names


def render_domains(result: dict[str, Any]) -> str:
    return _render("domains.html", domains=_domain_names(result.get("domains", [])))


def _record_suffix(rrset: dict[str, Any]) -> str:
    if rrset.get("ttl") in (None, ""):
        return ""
    return f" (ttl={rrset['ttl']})"


def render_records(result: dict[str, Any]) -> str:
    domain = str(result.get("domain") or "")
    groups: dict[str, list[dict[str, Any]]] = {}
    for rrset in result.get("rrsets", []):
        if not isinstance(rrset, dict):
            continue
        subname = str(rrset.get("subname") or "@")
        record_type = str(rrset.get("type", ""))
        values = [str(item) for item in rrset.get("records", [])]
        content = ", ".join(values)
        groups.setdefault(record_type, []).append(
            {
                "name": subname,
                "content": content,
                "values": values,
                "suffix": _record_suffix(rrset),
            }
        )
    rows = [{"type": t, "records": records} for t, records in groups.items()]
    return _render("records.html", domain=domain, groups=rows)
