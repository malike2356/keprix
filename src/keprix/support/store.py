"""File-backed support data store."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _data_root() -> Path:
    env = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if env:
        return Path(env)
    try:
        from keprix_cli.config import get_keprix_home

        return Path(get_keprix_home())
    except Exception:
        return Path.home() / ".keprix"


def support_home() -> Path:
    path = _data_root() / "support"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupportStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or support_home()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._tickets_path = self._dir / "tickets.json"
        self._incidents_path = self._dir / "incidents.json"
        self._checklist_path = self._dir / "onboarding_checklist.json"
        self._handoffs_path = self._dir / "handoffs.jsonl"
        self._privacy_path = self._dir / "privacy.json"

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list_tickets(self) -> list[dict[str, Any]]:
        return self._read_json(self._tickets_path, [])

    def save_ticket(self, ticket: dict[str, Any]) -> dict[str, Any]:
        tickets = self.list_tickets()
        tickets.append(ticket)
        self._write_json(self._tickets_path, tickets)
        return ticket

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        for ticket in self.list_tickets():
            if ticket["id"] == ticket_id:
                return ticket
        return None

    def update_ticket(self, ticket_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        tickets = self.list_tickets()
        for index, ticket in enumerate(tickets):
            if ticket["id"] != ticket_id:
                continue
            ticket.update(patch)
            tickets[index] = ticket
            self._write_json(self._tickets_path, tickets)
            return ticket
        return None

    def list_incidents(self) -> list[dict[str, Any]]:
        return self._read_json(self._incidents_path, [])

    def save_incident(self, incident: dict[str, Any]) -> dict[str, Any]:
        incidents = self.list_incidents()
        incidents.append(incident)
        self._write_json(self._incidents_path, incidents)
        return incident

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        for incident in self.list_incidents():
            if incident["id"] == incident_id:
                return incident
        return None

    def update_incident(self, incident_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        incidents = self.list_incidents()
        for index, incident in enumerate(incidents):
            if incident["id"] != incident_id:
                continue
            incident.update(patch)
            incidents[index] = incident
            self._write_json(self._incidents_path, incidents)
            return incident
        return None

    def get_checklist(self) -> list[dict[str, Any]]:
        return self._read_json(self._checklist_path, [])

    def save_checklist(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self._write_json(self._checklist_path, items)
        return items

    def append_handoff(self, record: dict[str, Any]) -> dict[str, Any]:
        record.setdefault("id", str(uuid.uuid4()))
        record.setdefault("created_at", _utcnow())
        with self._handoffs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        return record

    def get_privacy_settings(self) -> dict[str, Any]:
        return self._read_json(
            self._privacy_path,
            {"allow_contact_email": True, "allow_diagnostics_in_handoff": True},
        )

    def save_privacy_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        current = self.get_privacy_settings()
        current.update(settings)
        self._write_json(self._privacy_path, current)
        return current


_store: SupportStore | None = None


def get_support_store() -> SupportStore:
    global _store
    if _store is None:
        _store = SupportStore()
    return _store
