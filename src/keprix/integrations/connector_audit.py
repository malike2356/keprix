"""Scout audit metadata helpers for connector-backed playbook steps."""

from __future__ import annotations

from typing import Any

from keprix.integrations.connector_catalog import get_connector, load_connector_catalog


def audit_class_for_tools(tool_names: list[str]) -> str | None:
    """Map tool names to a connector audit class using catalog samples."""
    names = set(tool_names)
    for entry in load_connector_catalog():
        sample = entry.sample_playbook_node or {}
        data = dict(sample.get("data") or {})
        sample_tools = set(str(tool) for tool in list(data.get("tools") or []))
        if names & sample_tools:
            return entry.scout_audit_class
    return None


def enrich_run_event(event: dict[str, Any], *, step_config: dict[str, Any]) -> dict[str, Any]:
    """Add connector metadata to a playbook event payload when available."""
    connector_id = step_config.get("connector_id")
    tools = [str(tool) for tool in list(step_config.get("tools") or [])]
    audit_class = None
    if connector_id:
        entry = get_connector(str(connector_id))
        audit_class = entry.scout_audit_class if entry else None
    if audit_class is None and tools:
        audit_class = audit_class_for_tools(tools)
    if not connector_id and audit_class is None:
        return event
    enriched = dict(event)
    if connector_id:
        enriched["connector_id"] = str(connector_id)
    if audit_class:
        enriched["scout_audit_class"] = audit_class
    return enriched
