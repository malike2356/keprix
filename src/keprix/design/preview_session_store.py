"""Persisted sessions for the design live preview studio."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix_constants import get_keprix_home


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def preview_root() -> Path:
    root = get_keprix_home() / "design" / "preview"
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class PreviewSession:
    session_id: str
    root_path: str | None
    artifact_id: str | None
    entry_file: str
    selected_selector: str | None = None
    selected_html_snippet: str | None = None
    selected_meta: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PreviewSession":
        return cls(
            session_id=str(data["session_id"]),
            root_path=data.get("root_path"),
            artifact_id=data.get("artifact_id"),
            entry_file=str(data.get("entry_file") or "index.html"),
            selected_selector=data.get("selected_selector"),
            selected_html_snippet=data.get("selected_html_snippet"),
            selected_meta=dict(data.get("selected_meta") or {}),
            created_at=str(data.get("created_at") or _now()),
            updated_at=str(data.get("updated_at") or _now()),
        )


class PreviewSessionStore:
    def path_for(self, session_id: str) -> Path:
        return preview_root() / f"{session_id}.json"

    def create(self, *, root_path: str | None, artifact_id: str | None, entry_file: str) -> PreviewSession:
        session = PreviewSession(
            session_id=f"dp-{uuid4().hex[:10]}",
            root_path=root_path,
            artifact_id=artifact_id,
            entry_file=entry_file,
        )
        return self.save(session)

    def save(self, session: PreviewSession) -> PreviewSession:
        session.updated_at = _now()
        self.path_for(session.session_id).write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
        return session

    def get(self, session_id: str) -> PreviewSession | None:
        path = self.path_for(session_id)
        if not path.is_file():
            return None
        return PreviewSession.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list(self, limit: int = 20) -> list[PreviewSession]:
        paths = sorted(preview_root().glob("dp-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        return [PreviewSession.from_dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths[:limit]]
