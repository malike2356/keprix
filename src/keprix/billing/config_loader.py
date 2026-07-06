"""Load and validate product billing.yaml."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from keprix.billing.schema import BillingConfig

_CONFIG: BillingConfig | None = None
_CONFIG_PATH: Path | None = None


def _extension_billing_paths() -> list[Path]:
    paths: list[Path] = []
    raw = os.environ.get("KEPRIX_ACTIVE_EXTENSIONS", "").strip()
    for name in [part.strip() for part in raw.split(",") if part.strip()]:
        candidate = Path(__file__).resolve().parents[1] / "extensions" / name / "billing.yaml"
        if candidate.is_file():
            paths.append(candidate)
    return paths


def resolve_billing_config_path() -> Path | None:
    explicit = os.environ.get("KEPRIX_BILLING_CONFIG", "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_file() else None

    repo_default = Path(__file__).resolve().parents[3] / "config" / "billing.example.yaml"
    if repo_default.is_file() and os.environ.get("KEPRIX_BILLING_USE_EXAMPLE", "").lower() in {"1", "true", "yes"}:
        return repo_default

    extension_paths = _extension_billing_paths()
    if extension_paths:
        return extension_paths[0]

    return None


def load_billing_config(*, force_reload: bool = False) -> BillingConfig | None:
    global _CONFIG, _CONFIG_PATH
    if _CONFIG is not None and not force_reload:
        return _CONFIG

    path = resolve_billing_config_path()
    if path is None:
        _CONFIG = None
        _CONFIG_PATH = None
        return None

    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _CONFIG = BillingConfig.model_validate(raw)
    _CONFIG_PATH = path
    return _CONFIG


def billing_enabled() -> bool:
    if load_billing_config() is None:
        return False
    provider = os.environ.get("KEPRIX_BILLING_PROVIDER", "").strip().lower()
    if provider and provider != "stripe":
        return False
    if provider == "stripe" or os.environ.get("STRIPE_SECRET_KEY", "").strip():
        return True
    return os.environ.get("KEPRIX_BILLING_ENABLED", "").lower() in {"1", "true", "yes"}


def export_schema_json() -> str:
    return json.dumps(BillingConfig.model_json_schema(), indent=2)
