"""Boundary report generation and inventory validation."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from keprix.extraction.classifier import FeatureClass, FeatureRecord, is_governance_gated
from keprix.extraction.scanner import load_inventory_yaml, verify_inventory_sources

def load_inventory() -> list[FeatureRecord]:
    return [FeatureRecord.from_dict(row) for row in load_inventory_yaml()]


def validate_inventory(records: list[FeatureRecord] | None = None) -> list[str]:
    rows = records or load_inventory()
    errors: list[str] = []
    seen: set[str] = set()
    for record in rows:
        for field in ("id", "name", "subsystem", "owner", "source_path", "classification"):
            if not getattr(record, field, ""):
                errors.append(f"{record.id or 'unknown'}: missing {field}")
        if record.id in seen:
            errors.append(f"duplicate feature id: {record.id}")
        seen.add(record.id)
        if record.classification == FeatureClass.UNSAFE_OR_PRIVATE:
            if not record.rejected_reason:
                errors.append(f"{record.id}: rejected feature requires rejected_reason")
        elif record.classification in {
            FeatureClass.PUBLIC_CORE,
            FeatureClass.PUBLIC_OPTIONAL,
            FeatureClass.GOVERNANCE_ENTERPRISE,
            FeatureClass.PAID_MANAGED,
        }:
            if not record.rebuild_plan.strip():
                errors.append(f"{record.id}: requires rebuild_plan")
        if record.classification in {FeatureClass.PUBLIC_CORE, FeatureClass.PUBLIC_OPTIONAL}:
            if not record.target_prompt.strip():
                errors.append(f"{record.id}: public feature requires target_prompt")
        if is_governance_gated(record) and "governance" not in record.rebuild_plan.lower():
            errors.append(f"{record.id}: governance_enterprise rebuild_plan must mention governance gating")
    errors.extend(verify_inventory_sources(rows))
    return errors


def build_boundary_report(records: list[FeatureRecord] | None = None) -> dict[str, Any]:
    rows = records or load_inventory()
    by_class: dict[str, list[dict[str, Any]]] = {item.value: [] for item in FeatureClass}
    rejected: list[dict[str, Any]] = []
    governance_gated: list[dict[str, Any]] = []
    for record in rows:
        payload = asdict(record)
        payload["classification"] = record.classification.value
        by_class[record.classification.value].append(payload)
        if record.classification == FeatureClass.UNSAFE_OR_PRIVATE:
            rejected.append(payload)
        if is_governance_gated(record):
            governance_gated.append(payload)
    return {
        "total": len(rows),
        "by_classification": {key: len(value) for key, value in by_class.items()},
        "features": rows,
        "rejected": rejected,
        "governance_gated": governance_gated,
        "validation_errors": validate_inventory(rows),
    }


def product_boundaries_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "product" / "boundaries"
