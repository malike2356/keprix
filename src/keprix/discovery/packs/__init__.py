"""Vertical discovery packs (generic + property + health/social care)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from keprix.sheet_preprocess.models import ColumnRole
from keprix.sheet_preprocess.registry import (
    SheetTypeRegistration,
    register_pack_schema_provider,
    register_pack_sheet_type,
)

PACKS_DIR = Path(__file__).resolve().parent

_PACK_CACHE: dict[str, dict[str, Any]] = {}
_LOADED = False


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Pack manifest must be a mapping: {path}")
    return data


def load_vertical_packs(*, force: bool = False) -> dict[str, dict[str, Any]]:
    global _LOADED
    if _LOADED and not force:
        return dict(_PACK_CACHE)
    _PACK_CACHE.clear()
    for path in sorted(PACKS_DIR.glob("*.yaml")):
        pack = _load_yaml(path)
        pack_id = str(pack.get("id") or path.stem)
        _PACK_CACHE[pack_id] = pack
        _register_sheet_types(pack)
    # Schema provider once.
    register_pack_schema_provider(_schema_provider)
    _LOADED = True
    return dict(_PACK_CACHE)


def get_pack(pack_id: str) -> dict[str, Any] | None:
    load_vertical_packs()
    return _PACK_CACHE.get(pack_id)


def list_packs() -> list[dict[str, Any]]:
    load_vertical_packs()
    return [dict(v) for v in _PACK_CACHE.values()]


def _schema_provider(sheet_type: str) -> dict[str, Any] | None:
    load_vertical_packs()
    for pack in _PACK_CACHE.values():
        for st in pack.get("sheet_types") or []:
            if isinstance(st, dict) and st.get("id") == sheet_type:
                return {
                    "pack_id": pack.get("id"),
                    "sheet_type": sheet_type,
                    "columns": st.get("columns") or [],
                    "metrics": st.get("metrics") or [],
                    "stage_labels": pack.get("stage_labels") or {},
                }
    return None


def _register_sheet_types(pack: dict[str, Any]) -> None:
    pack_id = str(pack.get("id") or "pack")
    for st in pack.get("sheet_types") or []:
        if not isinstance(st, dict):
            continue
        sheet_type = str(st.get("id") or "").strip()
        if not sheet_type:
            continue
        markers = tuple(str(m) for m in (st.get("markers") or []))
        default_roles: dict[str, ColumnRole] = {}
        for col in st.get("columns") or []:
            if not isinstance(col, dict):
                continue
            name = str(col.get("name") or "")
            role_raw = str(col.get("role") or "").lower()
            role = _role_from_str(role_raw)
            if name and role:
                default_roles[name] = role
        register_pack_sheet_type(
            SheetTypeRegistration(
                sheet_type=sheet_type,
                markers=markers,
                default_roles=default_roles,
                pack_id=pack_id,
                description=str(st.get("description") or f"{pack_id} sheet type {sheet_type}"),
            )
        )


def _role_from_str(role: str) -> ColumnRole | None:
    mapping = {
        "company_name": ColumnRole.COMPANY_NAME,
        "contact_email": ColumnRole.CONTACT_EMAIL,
        "contact_phone": ColumnRole.CONTACT_PHONE,
        "identity": ColumnRole.IDENTITY,
        "stage": ColumnRole.STAGE,
        "url": ColumnRole.URL,
        "score": ColumnRole.SCORE,
        "metric": ColumnRole.METRIC,
        # No dedicated geo role in sheet_preprocess; keep as identity for mapping.
        "geo": ColumnRole.IDENTITY,
    }
    if role in mapping:
        return mapping[role]
    try:
        return ColumnRole(role)
    except Exception:  # noqa: BLE001
        return None
