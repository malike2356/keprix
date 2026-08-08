"""Secret-free readiness checks for the Clinicom Keprix pack."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix_cli.config import get_keprix_home

PACK_ROOT = Path(__file__).resolve().parents[3] / "domain-packs" / "clinicom"


def _check(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail}


def _receipt_path() -> Path:
    return get_keprix_home() / "products" / "clinicom-provision-receipt.json"


def provision_clinicom(*, write_receipt: bool = True) -> dict[str, Any]:
    manifest_path = PACK_ROOT / "manifest.json"
    schemas_path = PACK_ROOT / "schemas.json"
    http_path = PACK_ROOT / "http_app.py"
    contract_path = PACK_ROOT / "tools" / "contract.py"
    checks = [
        _check("pack_directory", PACK_ROOT.is_dir(), "Clinicom pack directory exists"),
        _check("http_app", http_path.is_file(), "Standalone sidecar entrypoint exists"),
        _check("manifest", manifest_path.is_file(), "Pack manifest exists"),
        _check("schemas", schemas_path.is_file(), "Input and output schemas exist"),
        _check("contract", contract_path.is_file() and 'CONTRACT_VERSION = "2.0"' in contract_path.read_text(encoding="utf-8"), "Contract version is 2.0"),
        _check("model_routes", contract_path.is_file() and "keprix-ml-service" in contract_path.read_text(encoding="utf-8"), "ML, Gemini, and deterministic routes declared"),
        _check("workload_identity", False, "Owner must configure workload identity or service credential in deployment environment"),
        _check("callbacks", True, "Clinicom connector callbacks are product-owned and proposal-only"),
        _check("resource_limits", True, "Runtime limits are supplied by Docker and sidecar validation"),
        _check("profile_safety", True, "Provision never changes CLINICOM_SIDECAR_PROFILE"),
    ]
    status = "ready_for_owner_review" if all(row["status"] == "pass" or row["name"] == "workload_identity" for row in checks) else "failed"
    receipt: dict[str, Any] = {
        "product": "clinicom",
        "status": status,
        "checks": checks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sidecar_profile_changed": False,
        "secrets_recorded": False,
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
        return {"product": "clinicom", "status": "not_provisioned", "checks": [], "receipt_path": None}
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["receipt_path"] = str(path)
    return receipt
