"""Version records for published Studio playbooks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import yaml


@dataclass
class PlaybookVersion:
    playbook_id: str
    version_hash: str
    published_at: str
    publisher_user_id: str
    scope: Literal["personal", "org"]
    status: Literal["draft", "pending_approval", "published", "rejected"]
    note: str = ""
    canvas_schema_version: int = 1
    scout_event_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def canonical_playbook_hash(yaml_doc: dict) -> str:
    import hashlib

    canonical = yaml.safe_dump(yaml_doc, sort_keys=True, allow_unicode=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class PlaybookVersionStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path.home() / ".keprix" / "playbooks"

    def record_publish(
        self,
        *,
        playbook_id: str,
        version_hash: str,
        publisher_user_id: str,
        scope: Literal["personal", "org"],
        status: Literal["draft", "pending_approval", "published", "rejected"],
        note: str = "",
        canvas_schema_version: int = 1,
        scout_event_id: str | None = None,
    ) -> PlaybookVersion:
        version = PlaybookVersion(
            playbook_id=playbook_id,
            version_hash=version_hash,
            published_at=datetime.now(timezone.utc).isoformat(),
            publisher_user_id=publisher_user_id,
            scope=scope,
            status=status,
            note=note,
            canvas_schema_version=canvas_schema_version,
            scout_event_id=scout_event_id,
        )
        directory = self._versions_dir(playbook_id)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{version_hash}.json").write_text(
            json.dumps(version.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (directory / "current.json").write_text(
            json.dumps({"version_hash": version_hash, "scope": scope}, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return version

    def list_versions(self, playbook_id: str) -> list[PlaybookVersion]:
        directory = self._versions_dir(playbook_id)
        if not directory.exists():
            return []
        versions: list[PlaybookVersion] = []
        for path in sorted(directory.glob("*.json")):
            if path.name == "current.json":
                continue
            versions.append(PlaybookVersion(**json.loads(path.read_text(encoding="utf-8"))))
        versions.sort(key=lambda item: item.published_at, reverse=True)
        return versions

    def get_current(self, playbook_id: str, *, scope: str = "personal") -> PlaybookVersion | None:
        directory = self._versions_dir(playbook_id)
        pointer = directory / "current.json"
        if not pointer.exists():
            return None
        data = json.loads(pointer.read_text(encoding="utf-8"))
        if data.get("scope") != scope:
            return None
        version_hash = str(data.get("version_hash") or "")
        path = directory / f"{version_hash}.json"
        if not path.exists():
            return None
        return PlaybookVersion(**json.loads(path.read_text(encoding="utf-8")))

    def update_status(
        self,
        *,
        playbook_id: str,
        version_hash: str,
        status: Literal["published", "rejected"],
        note: str | None = None,
    ) -> PlaybookVersion:
        path = self._versions_dir(playbook_id) / f"{version_hash}.json"
        if not path.exists():
            raise FileNotFoundError(version_hash)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = status
        if note:
            data["note"] = note
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return PlaybookVersion(**data)

    def _versions_dir(self, playbook_id: str) -> Path:
        safe = "".join(ch for ch in playbook_id if ch.isalnum() or ch in {"_", "-"})
        return self.root / safe / "versions"
