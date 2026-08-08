"""Pinned iLaud persona binding shared by Carina and Keprix."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PACK_ROOT = Path(__file__).resolve().parents[1]
PERSONA_PATH = PACK_ROOT / "personas" / "ilaud.yaml"
PINNED_VERSION = "ilaud@0.1.0"


def load_persona() -> dict[str, Any]:
    data = yaml.safe_load(PERSONA_PATH.read_text(encoding="utf-8")) or {}
    version = str(data.get("persona_version") or "")
    if version != PINNED_VERSION:
        raise ValueError(f"persona_pin_mismatch: expected {PINNED_VERSION}, got {version}")
    pin = data.get("pin") or {}
    if pin.get("carina") != PINNED_VERSION or pin.get("keprix") != PINNED_VERSION:
        raise ValueError("carina_and_keprix_must_share_same_persona_pin")
    return data


def persona_version() -> str:
    return str(load_persona()["persona_version"])


def owner_subject_id() -> str:
    return str(load_persona().get("owner_subject_id") or "owner-laud")
