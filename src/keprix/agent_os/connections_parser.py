"""Parser for connections.md tier matrix files."""

from __future__ import annotations

import re

from keprix.agent_os.connections_templates import ConnectionDomain, TIER1_DOMAINS, VALID_STATUSES, default_domains, render_connections_md

SECTION_RE = re.compile(r"^##\s+([a-z0-9_-]+)\s*$", re.MULTILINE)


def _parse_tools(value: str) -> list[str]:
    value = value.strip().strip("[]")
    if not value:
        return []
    return [item.strip().strip("'\"") for item in value.split(",") if item.strip()]


def parse_connections_md(markdown: str) -> list[ConnectionDomain]:
    if not markdown.strip():
        return default_domains()
    matches = list(SECTION_RE.finditer(markdown))
    parsed: dict[str, ConnectionDomain] = {}
    labels = {domain_id: label for domain_id, label, _examples in TIER1_DOMAINS}
    for index, match in enumerate(matches):
        domain_id = match.group(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        body = markdown[match.end() : end]
        fields: dict[str, str] = {}
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("- ") or ":" not in stripped:
                continue
            key, value = stripped[2:].split(":", 1)
            fields[key.strip()] = value.strip()
        status = fields.get("status") or "planned"
        if status not in VALID_STATUSES:
            status = "planned"
        parsed[domain_id] = ConnectionDomain(
            id=domain_id,
            label=fields.get("label") or labels.get(domain_id, domain_id.title()),
            status=status,
            tools=_parse_tools(fields.get("tools") or ""),
            integration_ref=None if fields.get("integration_ref") in {None, "", "null"} else fields.get("integration_ref"),
            service_account=str(fields.get("service_account") or "false").lower() == "true",
            notes=fields.get("notes") or "",
        )
    return [parsed.get(domain_id) or ConnectionDomain(id=domain_id, label=label) for domain_id, label, _examples in TIER1_DOMAINS]


def roundtrip_connections_md(markdown: str) -> str:
    return render_connections_md(parse_connections_md(markdown))
