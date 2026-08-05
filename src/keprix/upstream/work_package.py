"""Structured work packages for approved Hermes adoption work."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from keprix.upstream.hermes_monitor import AdoptionStatus, UpstreamFeature
from keprix.upstream.inventory_store import runtime_work_packages_dir

PARITY_GATES = [
    "bash scripts/check-tui-parity.sh",
    "bash scripts/check-tui-surpass-hermes.sh",
    "bash scripts/check-agent-parity.sh",
]

CATEGORY_PATH_HINTS: dict[str, list[str]] = {
    "tool": ["src/keprix/tools/", "tests/tools/", "src/keprix/security/"],
    "provider": ["src/keprix/agent/", "src/keprix/providers/", "tests/"],
    "routing": ["src/keprix/agent/", "config/", "tests/"],
    "memory": ["src/keprix/memory/", "src/keprix/agent/layers/", "tests/memory/"],
    "compression": ["src/keprix/agent/", "tests/"],
    "ui_cli": ["src/keprix/tui/", "tests/tui/", "docs/features/tui.md"],
    "security": ["src/keprix/security/", "tests/security/"],
    "integration": ["src/keprix/integrations/", "tests/"],
    "performance": ["src/keprix/", "tests/"],
    "platform": ["mobile/", "docs/"],
    "other": ["src/keprix/", "tests/"],
}


def build_work_package(
    feature: UpstreamFeature,
    *,
    prompt_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> Path:
    """Write a YAML work package for an approved feature. Returns the path."""
    if feature.adoption_status not in {
        AdoptionStatus.ADOPT,
        AdoptionStatus.ADOPT_WITH_HARDENING,
    }:
        raise ValueError(
            f"Work packages require approved adopt status; got {feature.adoption_status.value}"
        )

    dest_dir = Path(output_dir) if output_dir else runtime_work_packages_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_id = feature.feature_id.replace("/", "-")
    output_path = dest_dir / f"{safe_id}.yaml"

    paths = CATEGORY_PATH_HINTS.get(feature.category.value, CATEGORY_PATH_HINTS["other"])
    payload: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "feature_id": feature.feature_id,
        "name": feature.name,
        "description": feature.description,
        "category": feature.category.value,
        "hermes_version": feature.version_introduced,
        "release_url": feature.release_url,
        "adoption_status": feature.adoption_status.value,
        "keprix_equivalent": feature.keprix_equivalent,
        "adoption_prompt": str(prompt_path) if prompt_path else feature.adoption_prompt_id,
        "compare_summary": feature.compare_summary,
        "changelog_refs": feature.changelog_refs,
        "triage_notes": feature.triage_notes,
        "security_hardening": feature.security_implications,
        "target_paths": paths,
        "implementation_checklist": [
            "Rebuild capability against Keprix abstractions (do not merge Hermes git diffs).",
            "Follow docs/architecture/upstream-adoption-policy.md and core-product-boundary.md.",
            "Translate Hermes names via docs/architecture/hermes-to-keprix-rename-inventory.md.",
            "Add Scout/governance/egress hooks when tools, network, memory, or credentials are touched.",
            "Add functional + security tests under tests/.",
            "Run parity gates listed below before marking complete.",
            "Mark complete: keprix upstream complete <feature_id> --equivalent <capability-id>",
        ],
        "parity_gates": PARITY_GATES,
        "agent_task": {
            "summary": f"Adopt Hermes {feature.version_introduced} feature into Keprix: {feature.name}",
            "constraints": [
                "No silent merge of Hermes source into src/keprix/",
                "Human already approved this feature via keprix upstream decide",
                "Ship behind policy/feature flags when attack surface increases",
            ],
        },
    }
    output_path.write_text(
        yaml.safe_dump(payload, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    return output_path
