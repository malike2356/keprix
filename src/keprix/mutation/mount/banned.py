"""Banned mutation-mount targets (Soft Wall, RLS, first-class product modules)."""

from __future__ import annotations

from typing import Any

# Exact target ids that must never be mount/unmount'd via mutation.
BANNED_TARGET_IDS: frozenset[str] = frozenset(
    {
        "soft-wall",
        "soft_wall",
        "softwall",
        "hardline",
        "review-gateway",
        "review_gateway",
        "tenant-rls",
        "tenant_rls",
        "rls",
        "billing",
        "channel-shield",
        "channel_shield",
        "document-vault",
        "document_vault",
        "playbooks",
        "playbook",
        "crm",
        "pack-gate",
        "pack_gate",
        "governance",
        "vault",
        "auth",
        "security",
    }
)

# Substrings that mark a target as non-mutable via this path.
BANNED_SUBSTRINGS: tuple[str, ...] = (
    "soft_wall",
    "soft-wall",
    "hardline",
    "tenant_rls",
    "tenant-rls",
    "billing",
    "channel_shield",
    "channel-shield",
    "document_vault",
    "document-vault",
    "playbook",
    "pack_gate",
    "review_gateway",
    "/security/",
    "src/keprix/security",
    "src/keprix/billing",
    "src/keprix/auth",
    "src/keprix/vault",
    "src/keprix/governance",
)

# Seam provider ids that would strip Soft Wall / policy wrapping.
BANNED_PROVIDER_IDS: frozenset[str] = frozenset(
    {
        "shell.raw",
        "shell.unrestricted",
        "shell.no_policy",
        "fs.raw",
        "fs.unrestricted",
        "disable_soft_wall",
        "soft_wall_off",
    }
)

PRODUCT_MODULES_FIRST_CLASS: tuple[str, ...] = (
    "Playbooks",
    "CRM",
    "billing",
    "Document Vault",
    "Channel Shield",
)


class MountBanError(ValueError):
    """Raised when a mutation mount targets a forbidden area."""


def _norm(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def assert_mount_allowed(
    *,
    action: str,
    target_id: str,
    seam: str | None = None,
    provider_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Fail closed if the intent would weaken Soft Wall, RLS, or product cores."""
    tid = _norm(target_id)
    if not tid:
        raise MountBanError("target_id is required")
    if tid in BANNED_TARGET_IDS:
        raise MountBanError(f"target {target_id!r} is non-mutable via mutation mount")
    for needle in BANNED_SUBSTRINGS:
        if needle in tid or needle in tid.replace("-", "_"):
            raise MountBanError(
                f"target {target_id!r} matches banned pattern {needle!r}"
            )
    meta = metadata or {}
    if meta.get("disable_soft_wall") in (True, "true", "1", "yes", "on"):
        raise MountBanError("mutation mount cannot disable Soft Wall")
    if meta.get("bypass_soft_wall") in (True, "true", "1", "yes", "on"):
        raise MountBanError("mutation mount cannot disable Soft Wall")
    if meta.get("soft_wall") in (False, "off", "disable", "0", "false"):
        raise MountBanError("mutation mount cannot disable Soft Wall")
    if meta.get("drop_rls") in (True, "true", "1", "yes", "on"):
        raise MountBanError("mutation mount cannot drop tenant RLS")
    if action == "swap_provider":
        if not seam or not provider_id:
            raise MountBanError("swap_provider requires seam and provider_id")
        pid = _norm(provider_id)
        if pid in BANNED_PROVIDER_IDS or "no_policy" in pid or "unrestricted" in pid:
            raise MountBanError(
                f"provider {provider_id!r} is banned (would weaken Soft Wall)"
            )
        if meta.get("unwrap_policy") or meta.get("skip_policy_wrap"):
            raise MountBanError("mutation mount cannot unwrap policy Providers")
    # Never allow remote unsigned install flags.
    if meta.get("remote_url") or meta.get("fetch_unsigned"):
        raise MountBanError(
            "mutation mount cannot fetch unsigned remote plugins; owner policy required"
        )


def banned_summary() -> dict[str, Any]:
    return {
        "banned_target_ids": sorted(BANNED_TARGET_IDS),
        "banned_substrings": list(BANNED_SUBSTRINGS),
        "banned_provider_ids": sorted(BANNED_PROVIDER_IDS),
        "first_class_modules": list(PRODUCT_MODULES_FIRST_CLASS),
        "rules": [
            "no auto-rewrite of core Soft Wall",
            "no turning Playbooks/CRM/billing into plugins via mutation",
            "no fetching unsigned remote plugins without owner policy",
            "no dropping tenant RLS",
            "prefer skill/plugin mounts over writing arbitrary Python into src/keprix/",
        ],
    }
