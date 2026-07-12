"""Persist skill-to-automation links."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix_constants import get_keprix_home


def _links_path() -> Path:
    path = get_keprix_home() / "agent-os" / "automation-links.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class AutomationLink:
    link_id: str
    skill_slug: str
    automation_type: str
    automation_id: str
    edit_url: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AutomationLinkStore:
    def list(self, skill_slug: str | None = None) -> list[AutomationLink]:
        rows = self._load()
        links = [AutomationLink(**row) for row in rows]
        if skill_slug:
            links = [link for link in links if link.skill_slug == skill_slug]
        return links

    def add(self, *, skill_slug: str, automation_type: str, automation_id: str, edit_url: str, metadata: dict[str, Any] | None = None) -> AutomationLink:
        link = AutomationLink(
            link_id=str(uuid.uuid4()),
            skill_slug=skill_slug,
            automation_type=automation_type,
            automation_id=automation_id,
            edit_url=edit_url,
            metadata=metadata or {},
        )
        rows = self._load()
        rows.append(link.to_dict())
        _links_path().write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return link

    def remove(self, automation_type: str, automation_id: str) -> int:
        rows = self._load()
        kept = [row for row in rows if not (row.get("automation_type") == automation_type and row.get("automation_id") == automation_id)]
        _links_path().write_text(json.dumps(kept, indent=2), encoding="utf-8")
        return len(rows) - len(kept)

    def _load(self) -> list[dict[str, Any]]:
        path = _links_path()
        if not path.is_file():
            return []
        return json.loads(path.read_text(encoding="utf-8"))
