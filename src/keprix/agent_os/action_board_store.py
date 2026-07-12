"""Per-user Action Board pin configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix.agent_os.automation_link_store import AutomationLinkStore
from keprix.agent_os.run_ledger_store import RunLedgerStore
from keprix.agent_os.shortcut_registry import normalize_shortcut
from keprix_constants import get_keprix_home


@dataclass
class ActionPin:
    type: str
    id: str
    label: str
    pin_id: str = field(default_factory=lambda: f"pin_{uuid4().hex}")
    shortcut: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pin_id": self.pin_id,
            "type": self.type,
            "id": self.id,
            "label": self.label,
            "shortcut": self.shortcut,
        }


@dataclass
class ActionBoardConfig:
    user_id: str
    pins: list[ActionPin] = field(default_factory=list)
    shortcuts: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "pins": [pin.to_dict() for pin in self.pins],
            "shortcuts": self.shortcuts,
        }


def _board_path(user_id: str) -> Path:
    root = get_keprix_home() / "agent-os"
    root.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in user_id or "default")
    if safe in {"default", "user"}:
        return root / "action-board.json"
    return root / f"action-board-{safe}.json"


def _coerce_pin(data: dict[str, Any]) -> ActionPin:
    return ActionPin(
        pin_id=str(data.get("pin_id") or f"pin_{uuid4().hex}"),
        type=str(data.get("type") or "skill"),
        id=str(data.get("id") or ""),
        label=str(data.get("label") or data.get("id") or "Action"),
        shortcut=normalize_shortcut(data.get("shortcut")) if data.get("shortcut") else None,
    )


class ActionBoardStore:
    def load(self, user_id: str = "default") -> ActionBoardConfig:
        path = _board_path(user_id)
        if not path.exists():
            return ActionBoardConfig(user_id=user_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        pins = [_coerce_pin(pin) for pin in data.get("pins") or [] if isinstance(pin, dict)]
        shortcuts = {
            str(key): normalize_shortcut(value)
            for key, value in dict(data.get("shortcuts") or {}).items()
            if normalize_shortcut(value)
        }
        return ActionBoardConfig(user_id=user_id, pins=pins, shortcuts=shortcuts)

    def save(self, config: ActionBoardConfig) -> ActionBoardConfig:
        self._validate_shortcuts(config.pins)
        path = _board_path(config.user_id)
        path.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
        return config

    def add_pin(self, user_id: str, *, action_type: str, action_id: str, label: str | None = None, shortcut: str | None = None) -> ActionBoardConfig:
        config = self.load(user_id)
        pin = ActionPin(type=action_type, id=action_id, label=label or action_id, shortcut=normalize_shortcut(shortcut))
        config.pins.append(pin)
        config.shortcuts = {pin.id: pin.shortcut for pin in config.pins if pin.shortcut}
        return self.save(config)

    def remove_pin(self, user_id: str, pin_id: str) -> ActionBoardConfig:
        config = self.load(user_id)
        config.pins = [pin for pin in config.pins if pin.pin_id != pin_id]
        config.shortcuts = {pin.id: pin.shortcut for pin in config.pins if pin.shortcut}
        return self.save(config)

    def metrics(self) -> dict[str, Any]:
        entries = RunLedgerStore().list(limit=500)
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent = []
        for entry in entries:
            try:
                if datetime.fromisoformat(entry.created_at) >= cutoff:
                    recent.append(entry)
            except ValueError:
                continue
        return {
            "token_burn_24h": sum(entry.tokens for entry in recent),
            "runs_today": len(recent),
            "failed_runs": sum(1 for entry in recent if entry.status in {"failed", "error"}),
            "pending_approvals": sum(int(entry.output_summary.get("approval_backlog") or 0) for entry in entries),
        }

    def all_actions(self) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        skills_root = get_keprix_home() / "skills"
        if skills_root.exists():
            for path in sorted(skills_root.iterdir()):
                if (path / "SKILL.md").is_file():
                    actions.append({"type": "skill", "id": path.name, "label": path.name, "edit_url": f"/skills/{path.name}"})
        playbooks_root = get_keprix_home() / "playbooks" / "promoted"
        if playbooks_root.exists():
            for path in sorted(playbooks_root.glob("*.yaml")):
                actions.append({"type": "playbook", "id": path.stem, "label": path.stem, "edit_url": f"/playbooks/studio/{path.stem}"})
        apps_root = get_keprix_home() / "agent-apps"
        if apps_root.exists():
            for path in sorted(apps_root.iterdir()):
                if (path / "agent.yaml").is_file():
                    actions.append({"type": "agent_app", "id": path.name, "label": path.name, "edit_url": f"/agent-apps/{path.name}"})
        for link in AutomationLinkStore().list():
            data = link.to_dict()
            actions.append(
                {
                    "type": data["automation_type"],
                    "id": data["automation_id"],
                    "label": data["automation_id"],
                    "skill_slug": data["skill_slug"],
                    "edit_url": data["edit_url"],
                }
            )
        deduped: dict[tuple[str, str], dict[str, Any]] = {}
        for action in actions:
            deduped[(str(action["type"]), str(action["id"]))] = action
        return list(deduped.values())

    def _validate_shortcuts(self, pins: list[ActionPin]) -> None:
        seen: dict[str, str] = {}
        for pin in pins:
            if not pin.shortcut:
                continue
            if pin.shortcut in seen and seen[pin.shortcut] != pin.pin_id:
                raise ValueError(f"Duplicate shortcut: {pin.shortcut}")
            seen[pin.shortcut] = pin.pin_id
