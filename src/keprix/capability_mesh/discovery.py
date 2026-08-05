"""Generate mesh discovery text for self-knowledge / agent discoverability."""

from __future__ import annotations

from pathlib import Path

from keprix.capability_mesh.graph import CapabilityGraph, load_graph


def render_discovery_markdown(graph: CapabilityGraph | None = None) -> str:
    graph = graph or load_graph()
    lines = [
        "# Keprix capability mesh (agent discoverability)",
        "",
        "Workspace features link through shared object IDs and agent tools.",
        "Channel reachability means tools in `_KEPRIX_CORE_TOOLS` / `keprix-telegram`.",
        "",
        "## Features",
        "",
    ]
    for node in sorted(graph.nodes.values(), key=lambda n: n.id):
        tools = ", ".join(node.tools) if node.tools else "(none listed)"
        surfaces = ", ".join(node.channel_surfaces) if node.channel_surfaces else "-"
        lines.append(f"### {node.label} (`{node.id}`)")
        lines.append(f"- status: `{node.status}`")
        lines.append(f"- channels: {surfaces}")
        lines.append(f"- tools: {tools}")
        if node.notes:
            lines.append(f"- notes: {node.notes}")
        outs = graph.neighbors(node.id, direction="out")
        if outs:
            hops = "; ".join(
                f"{edge.relation} -> `{other.id}`"
                + (f" via `{edge.via_id_field}`" if edge.via_id_field else "")
                for edge, other in outs
            )
            lines.append(f"- links: {hops}")
        lines.append("")

    lines.extend(
        [
            "## Pilot verbs (Telegram / chat)",
            "",
            "- Book / slots / bookings: `vical_offer_slots`, `vical_create_booking`, `vical_list_bookings`, `vical_cancel_booking`",
            "- Calendar: `calendar_list_events`",
            "- Contacts: `contacts_search`, `contacts_get`",
            "- Companies House: `search:companies_house`, `get:company_profile`",
            "",
            "Regenerate: `PYTHONPATH=src python3 -m keprix.capability_mesh.discovery --write`",
            "",
        ]
    )
    return "\n".join(lines)


def default_discovery_path() -> Path:
    return Path(__file__).resolve().parent / "DISCOVERY.md"


def write_discovery(path: Path | None = None, graph: CapabilityGraph | None = None) -> Path:
    out = path or default_discovery_path()
    out.write_text(render_discovery_markdown(graph), encoding="utf-8")
    return out


TOOL_SEARCH_SYNONYMS: dict[str, list[str]] = {
    "vical_offer_slots": ["book", "booking", "slot", "slots", "appointment", "schedule", "vical"],
    "vical_create_booking": ["book", "booking", "schedule", "appointment", "vical"],
    "vical_list_bookings": ["bookings", "appointments", "upcoming", "vical"],
    "vical_cancel_booking": ["cancel", "unbook", "vical"],
    "calendar_list_events": ["calendar", "agenda", "events", "schedule"],
    "contacts_search": ["contact", "contacts", "person", "people", "email"],
    "contacts_get": ["contact", "contacts"],
}
