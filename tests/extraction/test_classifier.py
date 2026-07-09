"""Extraction classifier tests."""

from __future__ import annotations

from pathlib import Path

from keprix.extraction.classifier import (
    FeatureClass,
    FeatureRecord,
    is_customer_data_path,
    is_excluded_scan_path,
    is_governance_gated,
)


def test_governance_enterprise_features_are_gated() -> None:
    record = FeatureRecord(
        id="governance-demo",
        name="Governance policy",
        subsystem="governance",
        owner="managed-saas",
        source_path="billing/managed-governance-provisioning.ts",
        target_prompt="38",
        classification=FeatureClass.GOVERNANCE_ENTERPRISE,
        dependencies=[],
        data_touched=[],
        secrets_touched=[],
        tenant_scope="saas",
        rebuild_plan="Gate behind governance provider connection",
        test_mapping="tests/governance/",
        doc_mapping="docs/security/scope.md",
    )
    assert is_governance_gated(record)
    assert not is_governance_gated(
        FeatureRecord(
            id="memory",
            name="memory",
            subsystem="memory",
            owner="platform",
            source_path="memory/db.ts",
            target_prompt="06",
            classification=FeatureClass.PUBLIC_CORE,
            dependencies=[],
            data_touched=[],
            secrets_touched=[],
            tenant_scope="local",
            rebuild_plan="Rebuild memory",
            test_mapping="tests/memory/",
            doc_mapping="docs/memory/",
        )
    )


def test_customer_data_directories_are_excluded() -> None:
    assert is_customer_data_path("/data/tenant-data/acme")
    assert is_customer_data_path(Path("uploads/file.csv"))
    assert not is_customer_data_path("/src/memory/db.ts")


def test_env_files_are_excluded_from_scan() -> None:
    assert is_excluded_scan_path(".env")
    assert is_excluded_scan_path("config/.env.production")
    assert not is_excluded_scan_path("src/config.ts")
