"""Connections tier matrix service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keprix.agent_os.connections_parser import parse_connections_md
from keprix.agent_os.connections_templates import ConnectionDomain, SUGGESTED_TOOLS, default_domains, render_connections_md
from keprix.workspace.template_presets import workspace_root


def _root(workspace_id: str = "personal-os", workspace_path: str | None = None) -> Path:
    return Path(workspace_path).expanduser().resolve() if workspace_path else workspace_root(workspace_id)


class ConnectionsService:
    def load(self, *, workspace_id: str = "personal-os", workspace_path: str | None = None) -> list[ConnectionDomain]:
        path = _root(workspace_id, workspace_path) / "connections.md"
        if not path.is_file():
            return default_domains()
        return parse_connections_md(path.read_text(encoding="utf-8"))

    def init_template(self, *, workspace_id: str = "personal-os", workspace_path: str | None = None, seed_tools: list[str] | None = None) -> dict[str, Any]:
        root = _root(workspace_id, workspace_path)
        root.mkdir(parents=True, exist_ok=True)
        domains = default_domains(seed_tools)
        return self.save(domains, workspace_id=workspace_id, workspace_path=str(root))

    def save(self, domains: list[ConnectionDomain], *, workspace_id: str = "personal-os", workspace_path: str | None = None) -> dict[str, Any]:
        root = _root(workspace_id, workspace_path)
        root.mkdir(parents=True, exist_ok=True)
        md_path = root / "connections.md"
        json_path = root / "connections.json"
        md_path.write_text(render_connections_md(domains), encoding="utf-8")
        json_path.write_text(json.dumps({"domains": [domain.to_dict() for domain in domains]}, indent=2), encoding="utf-8")
        return {"path": str(md_path), "json_path": str(json_path), "domains": [domain.to_dict() for domain in domains]}

    def update_domain(
        self,
        domain_id: str,
        *,
        status: str,
        tools: list[str] | None = None,
        integration_ref: str | None = None,
        service_account: bool | None = None,
        notes: str | None = None,
        workspace_id: str = "personal-os",
        workspace_path: str | None = None,
    ) -> dict[str, Any]:
        domains = self.load(workspace_id=workspace_id, workspace_path=workspace_path)
        found = False
        for domain in domains:
            if domain.id != domain_id:
                continue
            found = True
            domain.status = status
            if tools is not None:
                domain.tools = tools
            if integration_ref is not None:
                domain.integration_ref = integration_ref
            if service_account is not None:
                domain.service_account = service_account
            if notes is not None:
                domain.notes = notes
        if not found:
            raise ValueError(f"Unknown connection domain: {domain_id}")
        return self.save(domains, workspace_id=workspace_id, workspace_path=workspace_path)

    def suggest_priority(self, *, workspace_id: str = "personal-os", workspace_path: str | None = None) -> list[dict[str, Any]]:
        domains = self.load(workspace_id=workspace_id, workspace_path=workspace_path)
        weights = {"tasks": 100, "calendar": 95, "comms": 90, "knowledge": 75, "customer": 70, "revenue": 65, "meetings": 55}
        rows = []
        for domain in domains:
            if domain.status == "live":
                continue
            rows.append(
                {
                    "domain": domain.id,
                    "label": domain.label,
                    "rank_score": weights.get(domain.id, 50),
                    "suggested_tools": SUGGESTED_TOOLS.get(domain.id, []),
                    "rationale": f"{domain.label} is a tier-1 operating surface; wiring it improves connection maturity.",
                }
            )
        return sorted(rows, key=lambda row: row["rank_score"], reverse=True)[:3]
