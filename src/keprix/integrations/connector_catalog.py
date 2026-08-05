"""Connector marketplace catalog for Studio and integration discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

AuthPattern = Literal["api_key", "oauth", "mcp", "sidecar", "none", "env"]
AuditClass = Literal[
    "external_read",
    "external_write",
    "messaging_send",
    "filesystem",
    "code_exec",
    "network_egress",
    "none",
]
Category = Literal["productivity", "data", "messaging", "ai", "devtools", "automation"]


@dataclass(frozen=True)
class ConnectorEntry:
    id: str
    label: str
    category: Category
    description: str
    icon: str
    auth_pattern: AuthPattern
    mcp_server_id: str | None = None
    hub_pack_id: str | None = None
    sidecar_id: str | None = None
    scout_audit_class: AuditClass = "external_read"
    docs_url: str = ""
    sample_playbook_node: dict[str, Any] = field(default_factory=dict)
    featured: bool = False
    tags: tuple[str, ...] = ()
    install_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "category": self.category,
            "description": self.description,
            "icon": self.icon,
            "auth_pattern": self.auth_pattern,
            "mcp_server_id": self.mcp_server_id,
            "hub_pack_id": self.hub_pack_id,
            "sidecar_id": self.sidecar_id,
            "scout_audit_class": self.scout_audit_class,
            "docs_url": self.docs_url,
            "sample_playbook_node": self.sample_playbook_node,
            "featured": self.featured,
            "tags": list(self.tags),
            "install_hint": self.install_hint,
        }


def load_connector_catalog() -> list[ConnectorEntry]:
    """Merge static connector seeds with live MCP manifest metadata."""
    entries = [_entry_from_raw(raw) for raw in _load_seed_rows()]
    mcp_entries = _mcp_entries_by_name()
    enriched: list[ConnectorEntry] = []
    for entry in entries:
        mcp_name = entry.mcp_server_id or entry.id
        mcp = mcp_entries.get(mcp_name)
        if not mcp:
            enriched.append(entry)
            continue
        enriched.append(
            ConnectorEntry(
                **{
                    **entry.to_dict(),
                    "description": entry.description or mcp.description,
                    "docs_url": entry.docs_url or mcp.docs_url,
                    "tags": tuple(entry.tags),
                }
            )
        )
    return sorted(enriched, key=lambda item: (not item.featured, item.label.lower()))


def get_connector(connector_id: str) -> ConnectorEntry | None:
    for entry in load_connector_catalog():
        if entry.id == connector_id:
            return entry
    return None


def catalog_install_status(
    connector_id: str,
    *,
    workspace_id: str = "default",
) -> dict[str, Any]:
    del workspace_id
    entry = get_connector(connector_id)
    if entry is None:
        return {"installed": False, "reason": "unknown_connector"}
    if entry.auth_pattern in {"none", "env", "api_key", "oauth"} and not entry.mcp_server_id and not entry.hub_pack_id:
        local = entry.auth_pattern in {"none", "env"} and "Coming soon" not in entry.install_hint
        return {
            "installed": local,
            "reason": "built_in" if local else "not_installable",
        }
    if entry.mcp_server_id:
        try:
            from keprix_cli.mcp_catalog import is_enabled, is_installed

            return {
                "installed": is_installed(entry.mcp_server_id),
                "enabled": is_enabled(entry.mcp_server_id),
                "reason": "mcp",
            }
        except Exception:
            return {"installed": False, "reason": "mcp_status_unavailable"}
    if entry.hub_pack_id:
        try:
            from keprix.hub.registry import get_pack_registry

            installed = get_pack_registry().get_installed(entry.hub_pack_id) is not None
            return {"installed": installed, "reason": "hub_pack"}
        except Exception:
            return {"installed": False, "reason": "hub_status_unavailable"}
    return {"installed": False, "reason": "not_installable"}


def install_connector(connector_id: str) -> dict[str, Any]:
    entry = get_connector(connector_id)
    if entry is None:
        return {"ok": False, "status": "not_found"}
    if entry.mcp_server_id:
        from keprix_cli.mcp_catalog import get_entry, install_entry

        mcp_entry = get_entry(entry.mcp_server_id)
        if mcp_entry is None:
            return {"ok": False, "status": "not_installable", "next_url": "/admin/mcp"}
        install_entry(mcp_entry)
        return {"ok": True, "status": "installed", "next_url": "/admin/mcp"}
    if entry.hub_pack_id:
        from keprix.hub.registry import get_pack_registry
        from keprix.hub.installer import install_pack

        found = get_pack_registry().find_catalog_pack(entry.hub_pack_id)
        if found is None:
            return {"ok": False, "status": "not_installable", "next_url": "/hub"}
        pack_dir, manifest = found
        result = install_pack(pack_dir, manifest, approved=True)
        return {"ok": result.get("status") == "installed", "status": str(result.get("status")), "next_url": "/hub"}
    if entry.sidecar_id:
        return {"ok": True, "status": "setup_required", "next_url": "/admin/mcp"}
    return {"ok": False, "status": "not_installable"}


def connector_categories() -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for entry in load_connector_catalog():
        counts[entry.category] = counts.get(entry.category, 0) + 1
    labels = {
        "productivity": "Productivity",
        "data": "Data",
        "messaging": "Messaging",
        "ai": "AI",
        "devtools": "Devtools",
        "automation": "Automation",
    }
    return [
        {"id": key, "label": labels.get(key, key.title()), "count": counts[key]}
        for key in sorted(counts)
    ]


def _load_seed_rows() -> list[dict[str, Any]]:
    path = Path(__file__).with_name("connector_seeds.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise ValueError("connector_seeds.yaml must contain a list")
    return [row for row in data if isinstance(row, dict)]


def _entry_from_raw(raw: dict[str, Any]) -> ConnectorEntry:
    return ConnectorEntry(
        id=str(raw["id"]),
        label=str(raw["label"]),
        category=str(raw["category"]),  # type: ignore[arg-type]
        description=str(raw.get("description") or ""),
        icon=str(raw.get("icon") or "Plug"),
        auth_pattern=str(raw.get("auth_pattern") or "none"),  # type: ignore[arg-type]
        mcp_server_id=raw.get("mcp_server_id"),
        hub_pack_id=raw.get("hub_pack_id"),
        sidecar_id=raw.get("sidecar_id"),
        scout_audit_class=str(raw.get("scout_audit_class") or "external_read"),  # type: ignore[arg-type]
        docs_url=str(raw.get("docs_url") or ""),
        sample_playbook_node=dict(raw.get("sample_playbook_node") or {}),
        featured=bool(raw.get("featured")),
        tags=tuple(str(tag) for tag in list(raw.get("tags") or [])),
        install_hint=str(raw.get("install_hint") or ""),
    )


def _mcp_entries_by_name() -> dict[str, Any]:
    try:
        from keprix_cli.mcp_catalog import list_catalog

        return {entry.name: entry for entry in list_catalog()}
    except Exception:
        return {}
