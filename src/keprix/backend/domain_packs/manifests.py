"""Domain pack manifest helpers (Prompt 30)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keprix.backend.domain_packs.schemas import DomainPackManifest, HIGH_STAKES_DOMAINS
from keprix.hub.manifests import PackManifest


def template_root() -> Path:
    return Path(__file__).resolve().parents[3] / "domain-packs" / "_template"


def load_template_manifest() -> dict[str, Any]:
    path = template_root() / "pack.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "domain_name": "example-domain",
        "version": "0.1.0",
        "jurisdictions": ["GH"],
        "common_tasks": ["Summarize domain concepts", "Draft checklist"],
        "disclaimers": ["This pack is informational only and not legal advice."],
        "limitations": ["Does not replace licensed professional review."],
        "can_do": ["Explain terminology", "Suggest workflow checklists"],
        "cannot_do": ["Provide binding legal or medical advice"],
        "tool_permissions": ["filesystem:read"],
        "localization_coverage": {"locales": ["en"], "fallback": "en"},
    }


def create_manifest_from_template(domain_name: str, *, jurisdictions: list[str] | None = None) -> DomainPackManifest:
    import uuid

    template = load_template_manifest()
    pack = DomainPackManifest.from_dict(
        {
            "id": str(uuid.uuid4()),
            "domain_name": domain_name,
            "version": template.get("version", "0.1.0"),
            "jurisdictions": jurisdictions or list(template.get("jurisdictions") or []),
            "common_tasks": list(template.get("common_tasks") or []),
            "disclaimers": list(template.get("disclaimers") or []),
            "limitations": list(template.get("limitations") or []),
            "can_do": list(template.get("can_do") or []),
            "cannot_do": list(template.get("cannot_do") or []),
            "tool_permissions": list(template.get("tool_permissions") or []),
            "localization_coverage": dict(template.get("localization_coverage") or {}),
            "playbooks": list(template.get("playbooks") or []),
            "data_schemas": list(template.get("data_schemas") or []),
            "tests": list(template.get("tests") or []),
        }
    )
    pack.review_required = domain_name.lower() in HIGH_STAKES_DOMAINS
    return pack


def to_hub_manifest(pack: DomainPackManifest) -> PackManifest:
    slug = pack.domain_name.replace("_", "-").lower()
    return PackManifest(
        name=slug,
        version=pack.version,
        type="domain_knowledge_pack",
        author="Keprix",
        license="MIT",
        description=f"Domain knowledge pack for {pack.domain_name}",
        permissions=list(pack.tool_permissions),
        files=[
            "pack.json",
            "glossary.json",
            "playbooks.json",
            "schemas.json",
            "README.md",
        ],
        dependencies=[],
        setup_requirements=[],
        data_touched=[f"~/.keprix/hub/installed/domain_knowledge_pack/{slug}"],
        network_hosts=[],
        risk_level="high" if pack.review_required else "medium",
        uninstall_plan=[f"remove domain pack {slug}"],
        tests=list(pack.tests),
        changelog={pack.version: f"Published domain pack {pack.domain_name}"},
        trust_label="official" if pack.review_status == "approved" else "community",
        review_score=pack.source_quality_score if pack.source_quality_score else None,
    )
