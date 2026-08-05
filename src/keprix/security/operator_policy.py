"""Operator-owned policy profiles (Prompt 297).

Operators choose strict / standard / permissive. Hard floors (child safety,
malware, weapons) never change. Sandboxes, egress, tool ACL, and Scout kill
switch remain enforceable under every profile.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class OperatorPolicyProfile(str, Enum):
    STRICT = "strict"
    STANDARD = "standard"
    PERMISSIVE = "permissive"


@dataclass(frozen=True)
class OperatorPolicyKnobs:
    """Profile-controlled knobs. Hard floors are never represented here."""

    dual_use_depth: str  # refuse | high_level | detailed
    package_install: str  # block | confirm | allow_sandbox
    browser_unknown_hosts: str  # block | egress_policy
    skill_first_mode: str  # never_bypass | warn_once
    third_party_mcp: str  # never | suggest
    child_safety_block: bool = True
    malware_block: bool = True
    weapons_block: bool = True
    sandboxes_enforced: bool = True
    egress_enforced: bool = True
    scout_kill_switch: bool = True


PROFILE_KNOBS: dict[OperatorPolicyProfile, OperatorPolicyKnobs] = {
    OperatorPolicyProfile.STRICT: OperatorPolicyKnobs(
        dual_use_depth="refuse",
        package_install="block",
        browser_unknown_hosts="block",
        skill_first_mode="never_bypass",
        third_party_mcp="never",
    ),
    OperatorPolicyProfile.STANDARD: OperatorPolicyKnobs(
        dual_use_depth="high_level",
        package_install="confirm",
        browser_unknown_hosts="egress_policy",
        skill_first_mode="never_bypass",
        third_party_mcp="suggest",
    ),
    OperatorPolicyProfile.PERMISSIVE: OperatorPolicyKnobs(
        dual_use_depth="detailed",
        package_install="allow_sandbox",
        browser_unknown_hosts="egress_policy",
        skill_first_mode="warn_once",
        third_party_mcp="suggest",
    ),
}

DUAL_USE_SECTIONS: dict[str, str] = {
    "refuse": (
        "Dual-use technical depth (operator profile: strict):\n"
        "- Refuse detailed dual-use technical guidance (weapons design, "
        "offensive cyber tradecraft, biological production).\n"
        "- Offer only high-level public-domain context when declining."
    ),
    "high_level": (
        "Dual-use technical depth (operator profile: standard):\n"
        "- Prefer high-level, defensive, or publicly documented explanations.\n"
        "- Do not provide step-by-step offensive or production guidance."
    ),
    "detailed": (
        "Dual-use technical depth (operator profile: permissive):\n"
        "- Detailed technical discussion is allowed when the operator has "
        "chosen permissive and the request stays within hard floors.\n"
        "- Sandboxes, egress policy, and Scout kill switch remain active.\n"
        "- Still refuse child safety, malware, and weapons production."
    ),
}


@dataclass
class OperatorPolicy:
    profile: OperatorPolicyProfile
    knobs: OperatorPolicyKnobs
    source: str = "default"
    product_id: str = ""
    workspace_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.value,
            "source": self.source,
            "product_id": self.product_id,
            "workspace_id": self.workspace_id,
            "knobs": asdict(self.knobs),
            "warning": (
                "permissive does not disable sandboxes, egress, hard floors, "
                "or Scout kill switch"
            ),
        }

    @property
    def dual_use_section(self) -> str:
        return DUAL_USE_SECTIONS.get(self.knobs.dual_use_depth, DUAL_USE_SECTIONS["high_level"])

    @property
    def skill_first_profile(self) -> str:
        if self.knobs.skill_first_mode == "warn_once":
            return "permissive"
        return "strict" if self.profile == OperatorPolicyProfile.STRICT else "standard"


def normalize_profile(raw: Any) -> OperatorPolicyProfile:
    text = str(raw or "").strip().lower()
    if text in {"high", "maximum", "strict"}:
        return OperatorPolicyProfile.STRICT
    if text in {"low", "permissive", "mythos"}:
        return OperatorPolicyProfile.PERMISSIVE
    if text in {"standard", "fable", "default", "medium"}:
        return OperatorPolicyProfile.STANDARD
    if text in {p.value for p in OperatorPolicyProfile}:
        return OperatorPolicyProfile(text)
    return OperatorPolicyProfile.STANDARD


def _workspace_policy_path() -> Path:
    from keprix_cli.config import get_keprix_home

    return get_keprix_home() / "operator_policy.json"


def _load_workspace_store() -> dict[str, Any]:
    path = _workspace_policy_path()
    if not path.exists():
        return {"default_profile": "standard", "workspaces": {}, "products": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"default_profile": "standard", "workspaces": {}, "products": {}}
    if not isinstance(data, dict):
        return {"default_profile": "standard", "workspaces": {}, "products": {}}
    data.setdefault("default_profile", "standard")
    data.setdefault("workspaces", {})
    data.setdefault("products", {})
    return data


def _save_workspace_store(data: dict[str, Any]) -> None:
    path = _workspace_policy_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _config_yaml_profile() -> Optional[OperatorPolicyProfile]:
    try:
        from keprix_cli.config import load_config

        cfg = load_config() or {}
        agent = cfg.get("agent") if isinstance(cfg.get("agent"), dict) else {}
        security = cfg.get("security") if isinstance(cfg.get("security"), dict) else {}
        raw = (
            agent.get("operator_policy_profile")
            or agent.get("policy_profile")
            or security.get("operator_profile")
            or security.get("operator_policy_profile")
        )
        if raw:
            return normalize_profile(raw)
    except Exception:
        pass
    return None


def get_operator_policy(
    ctx: Any = None,
    *,
    product_id: str | None = None,
    workspace_id: str | None = None,
    agent: Any = None,
) -> OperatorPolicy:
    """Resolve profile: product policy → workspace → config.yaml → STANDARD."""
    pid = (product_id or "").strip()
    wid = (workspace_id or "").strip() or "default"

    if ctx is not None:
        pid = pid or (getattr(ctx, "product_id", None) or "")
        wid = (getattr(ctx, "workspace_id", None) or wid or "default")
    else:
        try:
            from keprix.security.product_context import get_product_context_or_none

            live = get_product_context_or_none()
            if live is not None:
                pid = pid or (live.product_id or "")
                wid = live.workspace_id or wid
        except Exception:
            pass

    if agent is not None:
        explicit = getattr(agent, "_operator_policy_profile", None)
        if isinstance(explicit, str) and explicit.strip():
            profile = normalize_profile(explicit)
            return OperatorPolicy(
                profile=profile,
                knobs=PROFILE_KNOBS[profile],
                source="agent",
                product_id=pid,
                workspace_id=wid,
            )

    # 1) Product Scout policy
    if pid:
        try:
            from keprix.security.product_policy import get_policy

            policy = get_policy(pid)
            if policy:
                raw = (
                    policy.get("security_profile")
                    or policy.get("security_policy")
                    or (policy.get("governance") or {}).get("operator_profile")
                )
                if raw:
                    profile = normalize_profile(raw)
                    return OperatorPolicy(
                        profile=profile,
                        knobs=PROFILE_KNOBS[profile],
                        source="product_policy",
                        product_id=pid,
                        workspace_id=wid,
                    )
        except Exception:
            logger.debug("product policy lookup failed", exc_info=True)

    store = _load_workspace_store()
    # Explicit product override in operator store
    if pid and isinstance(store.get("products"), dict) and store["products"].get(pid):
        profile = normalize_profile(store["products"][pid])
        return OperatorPolicy(
            profile=profile,
            knobs=PROFILE_KNOBS[profile],
            source="operator_store_product",
            product_id=pid,
            workspace_id=wid,
        )

    # 2) Workspace setting
    workspaces = store.get("workspaces") if isinstance(store.get("workspaces"), dict) else {}
    if wid in workspaces:
        profile = normalize_profile(workspaces[wid])
        return OperatorPolicy(
            profile=profile,
            knobs=PROFILE_KNOBS[profile],
            source="workspace",
            product_id=pid,
            workspace_id=wid,
        )

    # 3) config.yaml
    cfg_profile = _config_yaml_profile()
    if cfg_profile is not None:
        return OperatorPolicy(
            profile=cfg_profile,
            knobs=PROFILE_KNOBS[cfg_profile],
            source="config.yaml",
            product_id=pid,
            workspace_id=wid,
        )

    # Default store default_profile or STANDARD
    profile = normalize_profile(store.get("default_profile") or "standard")
    return OperatorPolicy(
        profile=profile,
        knobs=PROFILE_KNOBS[profile],
        source="default",
        product_id=pid,
        workspace_id=wid,
    )


def set_operator_policy(
    profile: str | OperatorPolicyProfile,
    *,
    product_id: str | None = None,
    workspace_id: str | None = None,
    updated_by: str = "operator",
) -> OperatorPolicy:
    """Persist operator profile and audit the change."""
    resolved = normalize_profile(profile)
    pid = (product_id or "").strip()
    wid = (workspace_id or "").strip() or "default"
    store = _load_workspace_store()

    if pid:
        products = dict(store.get("products") or {})
        products[pid] = resolved.value
        store["products"] = products
        # Also mirror into Scout product_policy for enforcement consumers.
        try:
            from keprix.security.product_policy import apply_product_policy, get_policy

            existing = get_policy(pid) or {}
            governance = dict(existing.get("governance") or {})
            governance["operator_profile"] = resolved.value
            apply_product_policy(
                pid,
                {
                    **existing,
                    "security_profile": resolved.value,
                    "governance": governance,
                },
                updated_by=updated_by,
            )
        except Exception:
            logger.debug("mirror to product_policy failed", exc_info=True)
        source = "operator_store_product"
    else:
        workspaces = dict(store.get("workspaces") or {})
        workspaces[wid] = resolved.value
        store["workspaces"] = workspaces
        store["default_profile"] = resolved.value
        source = "workspace"

    _save_workspace_store(store)
    policy = OperatorPolicy(
        profile=resolved,
        knobs=PROFILE_KNOBS[resolved],
        source=source,
        product_id=pid,
        workspace_id=wid,
    )
    _audit_policy_change(policy, updated_by=updated_by)
    return policy


def profile_knob_diff() -> dict[str, dict[str, Any]]:
    """Return knob matrix for admin UI."""
    return {
        profile.value: asdict(knobs) for profile, knobs in PROFILE_KNOBS.items()
    }


def hard_floors_identical() -> bool:
    """Sanity check used by tests: hard floors never differ by profile."""
    floors = {
        (k.child_safety_block, k.malware_block, k.weapons_block, k.sandboxes_enforced, k.egress_enforced, k.scout_kill_switch)
        for k in PROFILE_KNOBS.values()
    }
    return len(floors) == 1 and True in {f[0] for f in floors}


def kill_switch_available_under_profile(profile: str | OperatorPolicyProfile) -> bool:
    """Permissive never disables Scout kill switch."""
    knobs = PROFILE_KNOBS[normalize_profile(profile)]
    return bool(knobs.scout_kill_switch)


def _audit_policy_change(policy: OperatorPolicy, *, updated_by: str) -> None:
    details = {
        **policy.to_dict(),
        "updated_by": updated_by,
    }
    try:
        from keprix.security.scout_integration import emit_scout_signal
        from keprix.security.scout_types import SignalCategory, SignalSeverity

        emit_scout_signal(
            SignalCategory.GOVERNANCE,
            SignalSeverity.WARNING if policy.profile == OperatorPolicyProfile.PERMISSIVE else SignalSeverity.INFO,
            "operator_policy.changed",
            f"profile:{policy.profile.value}",
            details,
            product_id=policy.product_id or None,
        )
    except TypeError:
        try:
            from keprix.security.scout_integration import emit_scout_signal
            from keprix.security.scout_types import SignalCategory, SignalSeverity

            emit_scout_signal(
                SignalCategory.GOVERNANCE,
                SignalSeverity.INFO,
                "operator_policy.changed",
                f"profile:{policy.profile.value}",
                details,
            )
        except Exception:
            pass
    except Exception:
        pass

    # Best-effort sync audit (API path also awaits audit_log).
    try:
        import asyncio

        from keprix.security.audit import audit_log

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            loop.create_task(
                audit_log(
                    "operator_policy.changed",
                    user_id=updated_by,
                    event_data=details,
                    severity="warning" if policy.profile == OperatorPolicyProfile.PERMISSIVE else "info",
                )
            )
        else:
            asyncio.run(
                audit_log(
                    "operator_policy.changed",
                    user_id=updated_by,
                    event_data=details,
                    severity="warning" if policy.profile == OperatorPolicyProfile.PERMISSIVE else "info",
                )
            )
    except Exception:
        logger.debug("operator policy audit_log skipped", exc_info=True)


def apply_operator_policy_to_agent(agent: Any, policy: OperatorPolicy | None = None) -> OperatorPolicy:
    """Stamp resolved policy onto an agent for skill-first / connector gates."""
    policy = policy or get_operator_policy(agent=agent)
    agent._operator_policy_profile = policy.profile.value
    agent._operator_policy = policy
    agent._skill_first_profile = policy.skill_first_profile
    # Connector: permissive/standard suggest; strict never auto-calls third-party.
    if policy.knobs.third_party_mcp == "never":
        agent._connector_first = True
        agent._connector_first_force_browser = False
    return policy
