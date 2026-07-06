"""Read-only reference scanner for optional external source trees."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from keprix.extraction.classifier import FeatureRecord, is_excluded_scan_path, is_customer_data_path
from keprix.extraction.license_check import check_file_license, license_conflicts_with_keprix
from keprix.extraction.secret_check import scan_file


def _default_source_roots() -> list[Path]:
    raw = os.environ.get("EXTRACTION_SOURCE_ROOTS", "").strip()
    if not raw:
        return []
    return [Path(part.strip()).expanduser() for part in raw.split(":") if part.strip()]


@dataclass
class ScanFinding:
    path: str
    kind: str
    detail: str


def inventory_path() -> Path:
    return Path(__file__).resolve().parent / "inventory.yaml"


def load_inventory_yaml() -> list[dict[str, Any]]:
    raw = yaml.safe_load(inventory_path().read_text(encoding="utf-8"))
    return list(raw.get("features") or [])


def scan_reference_file(path: Path) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    if is_excluded_scan_path(path):
        return findings
    if is_customer_data_path(path):
        findings.append(ScanFinding(str(path), "customer_data", "customer data path excluded"))
        return findings
    secret = scan_file(path)
    if secret["secrets"]:
        findings.append(ScanFinding(str(path), "secret", "secret pattern detected"))
    if secret["blocked_extensions"]:
        findings.append(ScanFinding(str(path), "secret", "blocked credential extension"))
    license_findings = check_file_license(path)
    for conflict in license_conflicts_with_keprix(license_findings):
        findings.append(ScanFinding(str(path), "license", conflict))
    return findings


def scan_reference_tree(root: Path) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    if not root.exists():
        return findings
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        findings.extend(scan_reference_file(path))
    return findings


def _resolve_source_path(rel: str, roots: list[Path]) -> Path | None:
    rel_path = Path(rel.lstrip("/"))
    for root in roots:
        candidate = root / rel_path
        if candidate.exists():
            return candidate
    return None


def verify_inventory_sources(
    records: list[FeatureRecord],
    *,
    source_roots: list[Path] | None = None,
) -> list[str]:
    roots = source_roots if source_roots is not None else _default_source_roots()
    if not roots:
        return []
    if not any(root.exists() for root in roots):
        return []
    errors: list[str] = []
    for record in records:
        if _resolve_source_path(record.source_path, roots) is None:
            errors.append(f"missing source path for {record.id}: {record.source_path}")
    return errors


def scan_inventory_records(records: list[FeatureRecord]) -> dict[str, list[ScanFinding]]:
    grouped: dict[str, list[ScanFinding]] = {}
    for record in records:
        roots = _default_source_roots()
        path = _resolve_source_path(record.source_path, roots)
        if path is None:
            continue
        grouped[record.id] = scan_reference_file(path)
    return grouped
