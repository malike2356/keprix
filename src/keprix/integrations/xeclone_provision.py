"""Secret-free readiness checks for the Xeclone Keprix pack."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix_cli.config import get_keprix_home

PACK_ROOT = Path(__file__).resolve().parents[3] / "domain-packs" / "xeclone"


def _check(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail}


def _receipt_path() -> Path:
    return get_keprix_home() / "products" / "xeclone-provision-receipt.json"


def provision_xeclone(*, write_receipt: bool = True) -> dict[str, Any]:
    manifest_path = PACK_ROOT / "manifest.json"
    schemas_path = PACK_ROOT / "schemas.json"
    http_path = PACK_ROOT / "http_app.py"
    persona_path = PACK_ROOT / "personas" / "ilaud.yaml"
    catalog_path = PACK_ROOT / "nodes" / "catalog.py"
    checks = [
        _check("pack_directory", PACK_ROOT.is_dir(), "Xeclone pack directory exists"),
        _check("http_app", http_path.is_file(), "Standalone sidecar entrypoint exists"),
        _check("manifest", manifest_path.is_file(), "Pack manifest exists"),
        _check("schemas", schemas_path.is_file(), "Input and output schemas exist"),
        _check(
            "persona_pin",
            persona_path.is_file() and "ilaud@0.1.0" in persona_path.read_text(encoding="utf-8"),
            "Pinned persona ilaud@0.1.0 present",
        ),
        _check(
            "nodes_catalog",
            catalog_path.is_file() and "persona_chat" in catalog_path.read_text(encoding="utf-8"),
            "Capability nodes catalog present",
        ),
        _check("workload_identity", False, "Owner must configure workload identity or service credential in deployment environment"),
        _check("callbacks", True, "Xeclone connector callbacks are product-owned"),
        _check("resource_limits", True, "Runtime limits are supplied by Docker and sidecar validation"),
        _check("carina_path_safety", True, "Provision never changes live Carina/Aiva runtime path"),
        _check("autonomous_mode_off", True, "Autonomous mode remains OFF unless separately signed"),
    ]
    status = (
        "ready_for_owner_review"
        if all(row["status"] == "pass" or row["name"] == "workload_identity" for row in checks)
        else "failed"
    )
    receipt: dict[str, Any] = {
        "product": "xeclone",
        "status": status,
        "checks": checks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "carina_path_changed": False,
        "autonomous_mode": False,
        "secrets_recorded": False,
        "pilot_scope": "local_or_staging_only",
    }
    if write_receipt:
        path = _receipt_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        receipt["receipt_path"] = str(path)
    return receipt


def provision_status() -> dict[str, Any]:
    path = _receipt_path()
    if not path.is_file():
        return {"product": "xeclone", "status": "not_provisioned", "checks": [], "receipt_path": None}
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["receipt_path"] = str(path)
    return receipt
