"""Connections tier matrix templates."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

TIER1_DOMAINS: tuple[tuple[str, str, list[str]], ...] = (
    ("revenue", "Revenue", ["stripe", "quickbooks", "sheets"]),
    ("customer", "Customer", ["crm", "support"]),
    ("calendar", "Calendar", ["google-workspace"]),
    ("comms", "Communications", ["slack", "email"]),
    ("tasks", "Tasks", ["clickup", "linear"]),
    ("meetings", "Meetings", ["fireflies", "transcripts"]),
    ("knowledge", "Knowledge", ["drive", "vault", "notion"]),
)
VALID_STATUSES = {"planned", "configuring", "live", "n/a"}
SUGGESTED_TOOLS = {
    "calendar": ["google-workspace"],
    "comms": ["google-workspace", "slack"],
    "knowledge": ["google-workspace", "notion", "vault"],
    "revenue": ["stripe", "quickbooks", "sheets"],
    "customer": ["crm", "support"],
    "tasks": ["clickup", "linear"],
    "meetings": ["fireflies", "transcript-folder"],
}


@dataclass
class ConnectionDomain:
    id: str
    label: str
    status: str = "planned"
    tools: list[str] = field(default_factory=list)
    integration_ref: str | None = None
    service_account: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_domains(seed_tools: list[str] | None = None) -> list[ConnectionDomain]:
    seed_tools = seed_tools or []
    domains: list[ConnectionDomain] = []
    for domain_id, label, examples in TIER1_DOMAINS:
        tools = [tool for tool in seed_tools if tool.lower() in {item.lower() for item in examples}]
        domains.append(ConnectionDomain(id=domain_id, label=label, tools=tools))
    return domains


def render_connections_md(domains: list[ConnectionDomain]) -> str:
    lines = [
        "# Connections",
        "",
        "> Tier-1 domains for OS maturity (274). Status: planned | configuring | live | n/a",
        "",
    ]
    for domain in domains:
        tools = "[" + ", ".join(domain.tools) + "]"
        lines.extend(
            [
                f"## {domain.id}",
                f"- label: {domain.label}",
                f"- status: {domain.status}",
                f"- tools: {tools}",
                f"- integration_ref: {domain.integration_ref or 'null'}",
                f"- service_account: {str(domain.service_account).lower()}",
                f"- notes: {domain.notes}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
