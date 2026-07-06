"""Legal acceptance records."""

from __future__ import annotations

import csv
import io
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _legal_dir() -> Path:
    env = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if env:
        root = Path(env) / "legal"
    else:
        try:
            from keprix_cli.config import get_keprix_home

            root = Path(get_keprix_home()) / "legal"
        except Exception:
            root = Path.home() / ".keprix" / "legal"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class AcceptanceStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._path = (base_dir or _legal_dir()) / "acceptances.json"
        self._rows: list[dict[str, Any]] = []
        if self._path.exists():
            self._rows = json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._rows, indent=2), encoding="utf-8")

    def record(
        self,
        *,
        workspace_id: str,
        user_id: str,
        policy_type: str,
        policy_version: str,
        accepted_ip_hash: str = "",
        user_agent_hash: str = "",
        source: str = "web_gate",
        api_caller_id: str | None = None,
    ) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "user_id": user_id,
            "api_caller_id": api_caller_id,
            "policy_type": policy_type,
            "policy_version": policy_version,
            "accepted_at": _utcnow(),
            "accepted_ip_hash": accepted_ip_hash,
            "user_agent_hash": user_agent_hash,
            "source": source,
        }
        self._rows = [
            r
            for r in self._rows
            if not (
                r.get("workspace_id") == workspace_id
                and r.get("user_id") == user_id
                and r.get("policy_type") == policy_type
                and r.get("policy_version") == policy_version
            )
        ]
        self._rows.append(row)
        self._save()
        return row

    def has_accepted(
        self,
        *,
        workspace_id: str,
        user_id: str,
        policy_type: str,
        policy_version: str,
    ) -> bool:
        return any(
            r.get("workspace_id") == workspace_id
            and r.get("user_id") == user_id
            and r.get("policy_type") == policy_type
            and r.get("policy_version") == policy_version
            for r in self._rows
        )

    def list_for_workspace(
        self,
        workspace_id: str,
        *,
        policy_type: str | None = None,
        policy_version: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = [r for r in self._rows if r.get("workspace_id") == workspace_id]
        if policy_type:
            rows = [r for r in rows if r.get("policy_type") == policy_type]
        if policy_version:
            rows = [r for r in rows if r.get("policy_version") == policy_version]
        return sorted(rows, key=lambda r: r.get("accepted_at", ""), reverse=True)

    def export_csv(self, workspace_id: str) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["user_id", "policy_type", "policy_version", "accepted_at", "source", "ip_hash"]
        )
        for row in self.list_for_workspace(workspace_id):
            writer.writerow(
                [
                    row.get("user_id", ""),
                    row.get("policy_type", ""),
                    row.get("policy_version", ""),
                    row.get("accepted_at", ""),
                    row.get("source", ""),
                    row.get("accepted_ip_hash", ""),
                ]
            )
        return buffer.getvalue()


_store: AcceptanceStore | None = None


def get_acceptance_store() -> AcceptanceStore:
    global _store
    if _store is None:
        _store = AcceptanceStore()
    return _store
