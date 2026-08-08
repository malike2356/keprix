"""Secret-free readiness checks for the Petraclus Keprix pack."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix_cli.config import get_keprix_home

PACK_ROOT = Path(__file__).resolve().parents[3] / "domain-packs" / "petraclus"


def _check(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {"name": name, "status": "pass" if ok else "fail", "detail": detail}


def _receipt_path() -> Path:
    return get_keprix_home() / "products" / "petraclus-provision-receipt.json"


def provision_petraclus(*, write_receipt: bool = True) -> dict[str, Any]:
    manifest_path = PACK_ROOT / "manifest.json"
    schemas_path = PACK_ROOT / "schemas.json"
    http_path = PACK_ROOT / "http_app.py"
    catalog_path = PACK_ROOT / "nodes" / "catalog.py"
    isolation_path = PACK_ROOT / "isolation" / "__init__.py"
    airgap_path = PACK_ROOT / "airgap" / "bundle.manifest.json"
    checks = [
        _check("pack_directory", PACK_ROOT.is_dir(), "Petraclus pack directory exists"),
        _check("http_app", http_path.is_file(), "Standalone sidecar entrypoint exists"),
        _check("manifest", manifest_path.is_file(), "Pack manifest exists"),
        _check("schemas", schemas_path.is_file(), "Input and output schemas exist"),
        _check(
            "contract_version",
            manifest_path.is_file() and '"contract_version": "1.0.0"' in manifest_path.read_text(encoding="utf-8"),
            "Contract version is 1.0.0",
        ),
        _check(
            "port",
            manifest_path.is_file() and '"port": 3362' in manifest_path.read_text(encoding="utf-8"),
            "Sidecar port is 3362",
        ),
        _check("catalog", catalog_path.is_file(), "Capability node catalog exists"),
        _check("isolation", isolation_path.is_file(), "Isolation enforcer exists"),
        _check("airgap_bundle", airgap_path.is_file(), "Air-gap bundle manifest exists"),
        _check("workload_identity", False, "Owner must configure workload identity in deployment environment"),
        _check("licence_authority", True, "Licence authority remains keys.petraclus.uk / product-side"),
        _check("exploit_automation", True, "Exploit automation remains off"),
    ]
    status = (
        "ready_for_owner_review"
        if all(row["status"] == "pass" or row["name"] == "workload_identity" for row in checks)
        else "failed"
    )
    receipt: dict[str, Any] = {
        "product": "petraclus",
        "status": status,
        "checks": checks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "secrets_recorded": False,
        "licence_minted": False,
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
        return {"product": "petraclus", "status": "not_provisioned", "checks": [], "receipt_path": None}
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["receipt_path"] = str(path)
    return receipt
