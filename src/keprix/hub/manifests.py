"""Pack manifest parsing and validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PACK_TYPES = {
    "skill_pack",
    "tool_pack",
    "domain_knowledge_pack",
    "app_template",
    "ui_template",
    "data_analysis_template",
    "research_workflow",
    "localization_pack",
    "connector_pack",
    "automation_pack",
}

RISK_LEVELS = {"low", "medium", "high"}


@dataclass
class PackManifest:
    name: str
    version: str
    type: str
    author: str
    license: str
    permissions: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    setup_requirements: list[str] = field(default_factory=list)
    data_touched: list[str] = field(default_factory=list)
    network_hosts: list[str] = field(default_factory=list)
    risk_level: str = "low"
    uninstall_plan: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    changelog: dict[str, str] = field(default_factory=dict)
    description: str = ""
    signature: str = ""
    review_score: float | None = None
    trust_label: str = "community"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PackManifest:
        return cls(
            name=str(data["name"]),
            version=str(data["version"]),
            type=str(data["type"]),
            author=str(data.get("author", "unknown")),
            license=str(data.get("license", "MIT")),
            permissions=list(data.get("permissions") or []),
            files=list(data.get("files") or []),
            dependencies=list(data.get("dependencies") or []),
            setup_requirements=list(data.get("setup_requirements") or []),
            data_touched=list(data.get("data_touched") or []),
            network_hosts=list(data.get("network_hosts") or []),
            risk_level=str(data.get("risk_level", "low")),
            uninstall_plan=list(data.get("uninstall_plan") or []),
            tests=list(data.get("tests") or []),
            description=str(data.get("description", "")),
            signature=str(data.get("signature", "")),
            review_score=data.get("review_score"),
            trust_label=str(data.get("trust_label", "community")),
            changelog={str(k): str(v) for k, v in (data.get("changelog") or {}).items()},
        )


def validate_manifest(manifest: PackManifest) -> list[str]:
    errors: list[str] = []
    if not manifest.name.strip():
        errors.append("name is required")
    if not manifest.version.strip():
        errors.append("version is required")
    if manifest.type not in PACK_TYPES:
        errors.append(f"unsupported pack type: {manifest.type}")
    if manifest.risk_level not in RISK_LEVELS:
        errors.append(f"invalid risk_level: {manifest.risk_level}")
    if not manifest.files:
        errors.append("files list is required")
    if not manifest.uninstall_plan:
        errors.append("uninstall_plan is required")
    return errors
