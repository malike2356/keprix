"""Mount intent types for mutation proposals (prompt 773)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

MountAction = Literal[
    "mount_plugin",
    "unmount_plugin",
    "mount_skill",
    "unmount_skill",
    "swap_provider",
]

MOUNT_ACTIONS: frozenset[str] = frozenset(
    {
        "mount_plugin",
        "unmount_plugin",
        "mount_skill",
        "unmount_skill",
        "swap_provider",
    }
)

ProposalStatus = Literal[
    "proposed",
    "approved",
    "denied",
    "mounted",
    "unmounted",
    "reversed",
]


@dataclass
class MountIntent:
    """Declarative capability change expressed as mount/unmount."""

    action: MountAction
    target_id: str
    seam: str | None = None
    provider_id: str | None = None
    previous_provider_id: str | None = None
    declared_tools: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MountIntent:
        action = str(data.get("action") or "")
        if action not in MOUNT_ACTIONS:
            raise ValueError(f"unknown mount action: {action}")
        return cls(
            action=action,  # type: ignore[arg-type]
            target_id=str(data.get("target_id") or ""),
            seam=data.get("seam"),
            provider_id=data.get("provider_id"),
            previous_provider_id=data.get("previous_provider_id"),
            declared_tools=list(data.get("declared_tools") or []),
            metadata=dict(data.get("metadata") or {}),
        )


def map_legacy_mutation_to_intent(
    *,
    kind: str,
    name: str,
    detail: dict[str, Any] | None = None,
) -> MountIntent:
    """Map common Mutation Engine proposal kinds onto mount actions."""
    detail = detail or {}
    kind_l = kind.strip().lower()
    if kind_l in {"add_plugin", "enable_plugin", "mount_plugin", "install_plugin"}:
        return MountIntent(action="mount_plugin", target_id=name, metadata=detail)
    if kind_l in {"remove_plugin", "disable_plugin", "unmount_plugin"}:
        return MountIntent(action="unmount_plugin", target_id=name, metadata=detail)
    if kind_l in {"add_skill", "enable_skill", "mount_skill"}:
        return MountIntent(action="mount_skill", target_id=name, metadata=detail)
    if kind_l in {"remove_skill", "disable_skill", "unmount_skill"}:
        return MountIntent(action="unmount_skill", target_id=name, metadata=detail)
    if kind_l in {"swap_provider", "set_provider", "change_provider"}:
        return MountIntent(
            action="swap_provider",
            target_id=name or str(detail.get("seam") or "seam"),
            seam=str(detail.get("seam") or name),
            provider_id=str(detail.get("provider_id") or detail.get("provider") or ""),
            previous_provider_id=detail.get("previous_provider_id"),
            metadata=detail,
        )
    raise ValueError(f"cannot map mutation kind {kind!r} to a mount action")


def skill_plugin_id(skill_name: str) -> str:
    name = skill_name.strip()
    if name.startswith("skill:"):
        return name
    return f"skill:{name}"


def mutation_ledger_id(proposal_id: str) -> str:
    return f"mutation-mount:{proposal_id}"
