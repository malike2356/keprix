"""Extraction inventory and report tests."""

from __future__ import annotations

from keprix.extraction.classifier import FeatureClass
from keprix.extraction.report import build_boundary_report, load_inventory, validate_inventory


def test_feature_inventory_includes_required_metadata() -> None:
    records = load_inventory()
    assert records
    for record in records:
        assert record.owner
        assert record.source_path
        if record.classification in {FeatureClass.PUBLIC_CORE, FeatureClass.PUBLIC_OPTIONAL}:
            assert record.target_prompt


def test_public_core_features_have_rebuild_plan() -> None:
    records = load_inventory()
    public = [row for row in records if row.classification == FeatureClass.PUBLIC_CORE]
    assert public
    for record in public:
        assert record.rebuild_plan.strip()


def test_rejected_features_include_reason() -> None:
    records = load_inventory()
    rejected = [row for row in records if row.classification == FeatureClass.UNSAFE_OR_PRIVATE]
    assert rejected
    for record in rejected:
        assert record.rejected_reason.strip()


def test_inventory_validates_clean() -> None:
    assert validate_inventory() == []


def test_boundary_report_groups_classifications() -> None:
    report = build_boundary_report()
    assert report["total"] >= 15
    assert report["validation_errors"] == []
    assert report["by_classification"]["public_core"] >= 5
    assert report["governance_gated"]
