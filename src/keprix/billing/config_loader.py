"""Load and validate product billing.yaml."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from keprix.billing.schema import BillingConfig
from keprix.billing.stripe.credentials import stripe_credentials_configured

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
        if not path.is_absolute():
            repo_root = Path(__file__).resolve().parents[3]
            path = (repo_root / path).resolve()
        return path if path.is_file() else None

    repo_default = Path(__file__).resolve().parents[3] / "config" / "billing.example.yaml"
    if repo_default.is_file() and os.environ.get("KEPRIX_BILLING_USE_EXAMPLE", "").lower() in {"1", "true", "yes"}:
        return repo_default

    # Prefer local billing.yaml when present (gitignored product config).
    local_billing = Path(__file__).resolve().parents[3] / "config" / "billing.yaml"
    if local_billing.is_file() and os.environ.get("KEPRIX_BILLING_ENABLED", "").lower() in {"1", "true", "yes"}:
        return local_billing

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


def resolve_billing_config_write_path() -> Path:
    """Path used when the admin GUI saves plan price pins.

    Never write over billing.example.yaml; prefer config/billing.yaml.
    """
    current = resolve_billing_config_path()
    repo_root = Path(__file__).resolve().parents[3]
    local = repo_root / "config" / "billing.yaml"
    if current is not None and current.name != "billing.example.yaml":
        return current
    return local


def save_billing_config(config: BillingConfig, *, path: Path | None = None) -> Path:
    """Persist billing config and refresh the in-memory cache."""
    global _CONFIG, _CONFIG_PATH
    target = path or resolve_billing_config_write_path()
    if target.name == "billing.example.yaml":
        raise ValueError("Refusing to overwrite billing.example.yaml; use config/billing.yaml")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = config.model_dump(mode="python", exclude_none=True)
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, default_flow_style=False)
    header = (
        "# Managed by Keprix admin billing GUI and/or operators.\n"
        "# Stripe price IDs must come from verlox/.access/.stripe-credentials-and-price-id.md.\n"
        "# Never create new Stripe products or prices from this file.\n"
    )
    target.write_text(header + text, encoding="utf-8")
    _CONFIG = config
    _CONFIG_PATH = target
    return target


def billing_enabled() -> bool:
    if load_billing_config() is None:
        return False
    explicit = os.environ.get("KEPRIX_BILLING_ENABLED", "").strip().lower()
    if explicit in {"0", "false", "no", "off"}:
        return False
    provider = os.environ.get("KEPRIX_BILLING_PROVIDER", "").strip().lower()
    if provider and provider != "stripe":
        return False
    if provider == "stripe" or stripe_credentials_configured():
        return True
    return explicit in {"1", "true", "yes"}


def export_schema_json() -> str:
    return json.dumps(BillingConfig.model_json_schema(), indent=2)
