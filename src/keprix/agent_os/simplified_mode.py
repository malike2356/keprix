"""Simplified mode configuration and route filtering."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keprix_constants import get_keprix_home


ADVANCED_PREFIXES = (
    "/playbooks/studio",
    "/agent-studio",
    "/admin/coding",
    "/control-center",
    "/admin/tools",
    "/admin/mcp",
    "/browser",
)

ADVANCED_NAV_IDS = {
    "agent-studio",
    "coding-adoption",
    "control-center",
    "tools-adoption",
    "mcp",
    "browser-adoption",
}


@dataclass
class SimplifiedModeConfig:
    simplified_mode: bool = False
    hide_terminal_coding: bool = True
    documents_read_only: bool = False
    allowed_paths: list[str] = field(default_factory=lambda: ["/agent-os", "/agent-apps", "/chat", "/documents", "/home", "/launcher", "/settings"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "simplified_mode": self.simplified_mode,
            "hide_terminal_coding": self.hide_terminal_coding,
            "documents_read_only": self.documents_read_only,
            "allowed_paths": self.allowed_paths,
        }


def _config_path() -> Path:
    root = get_keprix_home() / "agent-os"
    root.mkdir(parents=True, exist_ok=True)
    return root / "simplified-mode.json"


def get_simplified_mode() -> SimplifiedModeConfig:
    path = _config_path()
    if not path.exists():
        return SimplifiedModeConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    return SimplifiedModeConfig(
        simplified_mode=bool(data.get("simplified_mode", False)),
        hide_terminal_coding=bool(data.get("hide_terminal_coding", True)),
        documents_read_only=bool(data.get("documents_read_only", False)),
        allowed_paths=list(data.get("allowed_paths") or SimplifiedModeConfig().allowed_paths),
    )


def set_simplified_mode(config: SimplifiedModeConfig) -> SimplifiedModeConfig:
    _config_path().write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
    return config


def blocked_path(path: str, config: SimplifiedModeConfig | None = None) -> bool:
    cfg = config or get_simplified_mode()
    if not cfg.simplified_mode:
        return False
    if path in {"/agent-os", "/agent-apps", "/chat", "/documents", "/home", "/launcher"}:
        return False
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in ADVANCED_PREFIXES)


def filter_navigation(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cfg = get_simplified_mode()
    if not cfg.simplified_mode:
        return items
    return [
        item
        for item in items
        if item.get("id") not in ADVANCED_NAV_IDS and not blocked_path(str(item.get("href") or ""), cfg)
    ]
