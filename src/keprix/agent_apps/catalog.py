"""Curated agent app catalog and template install."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from keprix.agent_apps.registry import get_agent_app_registry

_CATALOG_ROOT = Path(__file__).resolve().parent / "catalog"


def catalog_root() -> Path:
    return _CATALOG_ROOT


def load_catalog_index() -> dict[str, Any]:
    index_path = _CATALOG_ROOT / "index.json"
    if not index_path.exists():
        return {"templates": []}
    return json.loads(index_path.read_text(encoding="utf-8"))


def list_catalog_templates(
    *,
    category: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    templates = list(load_catalog_index().get("templates") or [])
    if category:
        templates = [item for item in templates if item.get("category") == category]
    if query:
        needle = query.lower().strip()
        templates = [
            item
            for item in templates
            if needle in str(item.get("display_name", "")).lower()
            or needle in str(item.get("description", "")).lower()
            or needle in str(item.get("id", "")).lower()
        ]
    return templates


def get_catalog_template(template_id: str) -> dict[str, Any] | None:
    for item in list_catalog_templates():
        if item.get("id") == template_id:
            enriched = dict(item)
            readme = _CATALOG_ROOT / template_id / "README.md"
            if readme.exists():
                enriched["readme_excerpt"] = readme.read_text(encoding="utf-8")[:1200]
            return enriched
    return None


def template_dir(template_id: str) -> Path | None:
    path = _CATALOG_ROOT / template_id
    if path.is_dir() and (path / "agent.yaml").exists():
        return path
    return None


def install_catalog_template(template_id: str) -> dict[str, Any]:
    source = template_dir(template_id)
    if source is None:
        raise FileNotFoundError(f"Catalog template not found: {template_id}")
    registry = get_agent_app_registry()
    validation = registry.validate_only(source)
    if not validation.get("valid"):
        raise ValueError(validation.get("error", "Invalid catalog template"))
    return registry.install(source, source="template", source_id=template_id)


def merge_domain_pack_templates(templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Optional hook for domain packs; returns additional catalog entries."""
    packs_root = Path(__file__).resolve().parents[2].parent / "domain-packs"
    if not packs_root.is_dir():
        return templates
    merged = list(templates)
    for pack_dir in sorted(packs_root.iterdir()):
        index_path = pack_dir / "agent-apps" / "index.json"
        if not index_path.exists():
            continue
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for item in payload.get("templates") or []:
            enriched = dict(item)
            enriched["source"] = "domain_pack"
            enriched["pack_id"] = pack_dir.name
            merged.append(enriched)
    return merged
