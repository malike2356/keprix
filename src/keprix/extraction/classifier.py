"""Feature classification for legacy-to-Keprix extraction boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class FeatureClass(str, Enum):
    PUBLIC_CORE = "public_core"
    PUBLIC_OPTIONAL = "public_optional"
    PAID_MANAGED = "paid_managed"
    GOVERNANCE_ENTERPRISE = "governance_enterprise"
    UNSAFE_OR_PRIVATE = "unsafe_or_private"


CLASS_DESCRIPTIONS: dict[FeatureClass, str] = {
    FeatureClass.PUBLIC_CORE: "Suitable for free self-host; rebuild in Keprix.",
    FeatureClass.PUBLIC_OPTIONAL: "Useful but dependency-heavy; ship as optional plugin or pack.",
    FeatureClass.PAID_MANAGED: "Belongs to managed SaaS products; stub or integration hook only.",
    FeatureClass.GOVERNANCE_ENTERPRISE: "Paid governance or trust control; gate behind governance provider connection.",
    FeatureClass.UNSAFE_OR_PRIVATE: "Not suitable for Keprix; do not port.",
}

CUSTOMER_DATA_DIR_NAMES = {
    "tenant-data",
    "customer-data",
    "uploads",
    "user-uploads",
    "private",
    "backups",
    "snapshots",
}

EXCLUDED_SCAN_SEGMENTS = {
    ".env",
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    "vendor",
    "__pycache__",
}

EXCLUDED_SCAN_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "secrets.json",
}


@dataclass(frozen=True)
class FeatureRecord:
    id: str
    name: str
    subsystem: str
    owner: str
    source_path: str
    target_prompt: str
    classification: FeatureClass
    dependencies: list[str]
    data_touched: list[str]
    secrets_touched: list[str]
    tenant_scope: str
    rebuild_plan: str
    test_mapping: str
    doc_mapping: str
    rejected_reason: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeatureRecord:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            subsystem=str(data["subsystem"]),
            owner=str(data["owner"]),
            source_path=str(data["source_path"]),
            target_prompt=str(data.get("target_prompt", "")),
            classification=FeatureClass(str(data["classification"])),
            dependencies=list(data.get("dependencies") or []),
            data_touched=list(data.get("data_touched") or []),
            secrets_touched=list(data.get("secrets_touched") or []),
            tenant_scope=str(data.get("tenant_scope", "none")),
            rebuild_plan=str(data.get("rebuild_plan", "")),
            test_mapping=str(data.get("test_mapping", "")),
            doc_mapping=str(data.get("doc_mapping", "")),
            rejected_reason=str(data.get("rejected_reason", "")),
        )


def classify_feature(record: FeatureRecord) -> FeatureClass:
    return record.classification


def is_governance_gated(record: FeatureRecord | FeatureClass) -> bool:
    value = record if isinstance(record, FeatureClass) else record.classification
    return value == FeatureClass.GOVERNANCE_ENTERPRISE


def is_customer_data_path(path: Path | str) -> bool:
    parts = {part.lower() for part in Path(path).parts}
    return bool(parts & CUSTOMER_DATA_DIR_NAMES)


def is_excluded_scan_path(path: Path | str) -> bool:
    candidate = Path(path)
    if candidate.name in EXCLUDED_SCAN_FILENAMES:
        return True
    if candidate.suffix == ".env":
        return True
    return any(part in EXCLUDED_SCAN_SEGMENTS for part in candidate.parts)
