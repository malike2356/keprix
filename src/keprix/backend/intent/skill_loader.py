"""Workspace domain resolution for intent schema loading."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _data_root() -> Path:
    env = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if env:
        return Path(env)
    try:
        from keprix_cli.config import get_keprix_home

        return Path(get_keprix_home())
    except Exception:
        return Path.home() / ".keprix"


class SkillLoader:
    """Tracks which domain packs are active per workspace."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or (_data_root() / "intent")
        self._base.mkdir(parents=True, exist_ok=True)
        self._workspace_path = self._base / "workspace_domains.json"
        self._overrides: dict[str, list[str]] = {}
        if self._workspace_path.exists():
            raw = json.loads(self._workspace_path.read_text(encoding="utf-8"))
            self._overrides = {str(k): list(v) for k, v in raw.items()}

    def _save(self) -> None:
        self._workspace_path.write_text(
            json.dumps(self._overrides, indent=2),
            encoding="utf-8",
        )

    def set_loaded_domains(self, workspace_id: str, domains: list[str]) -> None:
        self._overrides[workspace_id] = sorted(set(domains))
        self._save()

    def clear_workspace(self, workspace_id: str) -> None:
        self._overrides.pop(workspace_id, None)
        self._save()

    def get_loaded_domains(self, workspace_id: str) -> list[str]:
        explicit = set(self._overrides.get(workspace_id, []))
        try:
            from keprix.hub.registry import PackRegistry

            for pack in PackRegistry().list_installed():
                if not pack.enabled:
                    continue
                manifest = pack.manifest or {}
                domain = str(manifest.get("domain") or manifest.get("intent_domain") or "").strip()
                if not domain:
                    name = pack.name.replace("-", "_")
                    if pack.type in {"domain_knowledge_pack", "localization_pack"}:
                        domain = name
                if domain:
                    explicit.add(domain)
        except Exception:
            pass
        return sorted(explicit)


_skill_loader: SkillLoader | None = None


def get_skill_loader() -> SkillLoader:
    global _skill_loader
    if _skill_loader is None:
        _skill_loader = SkillLoader()
    return _skill_loader


def reset_skill_loader(base_dir: Path | None = None) -> SkillLoader:
    global _skill_loader
    _skill_loader = SkillLoader(base_dir=base_dir)
    return _skill_loader
