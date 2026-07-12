"""Validate Obsidian starter vault conventions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keprix.vault.vault_init_service import MANIFEST_REL

REQUIRED_FOLDERS = ["00-inbox", "01-projects", "02-areas", "03-resources", "04-archive", "templates", ".keprix"]
REQUIRED_TEMPLATES = ["daily-note", "meeting", "research-summary"]


def load_vault_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path).expanduser().resolve() / MANIFEST_REL
    if not manifest_path.is_file():
        raise ValueError("Vault manifest missing: .keprix/vault-manifest.json")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def validate_vault(path: str | Path) -> dict[str, Any]:
    root = Path(path).expanduser().resolve()
    errors: list[str] = []
    manifest: dict[str, Any] = {}
    if not root.exists():
        errors.append(f"Vault path does not exist: {root}")
    try:
        manifest = load_vault_manifest(root)
    except Exception as exc:
        errors.append(str(exc))
    for folder in REQUIRED_FOLDERS:
        if not (root / folder).is_dir():
            errors.append(f"Missing folder: {folder}")
    if not (root / "KEPRIX.md").is_file():
        errors.append("Missing KEPRIX.md")
    else:
        content = (root / "KEPRIX.md").read_text(encoding="utf-8")
        for phrase in ["Standing instructions for agents", "Folder map", "00-inbox"]:
            if phrase not in content:
                errors.append(f"KEPRIX.md missing section: {phrase}")
    for template in REQUIRED_TEMPLATES:
        template_path = root / "templates" / f"{template}.md"
        if not template_path.is_file():
            errors.append(f"Missing template: {template}")
        elif "{{date}}" not in template_path.read_text(encoding="utf-8"):
            errors.append(f"Template missing {{date}} placeholder: {template}")
    return {"ok": not errors, "path": str(root), "manifest": manifest, "errors": errors}
