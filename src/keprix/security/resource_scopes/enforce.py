"""Enforce resource-scoped tool ACL decisions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from keprix.security.resource_scopes.extract import ExtractionResult, extract_resources
from keprix.security.resource_scopes.grants import ActorType, ResourceGrantStore, get_resource_grant_store
from keprix.security.resource_scopes.registry import SERVICE_RESOURCE_REGISTRY, ActionClass

logger = logging.getLogger(__name__)

# Dangerous actions fail closed when the target resource cannot be determined.
FAIL_CLOSED_ACTIONS: frozenset[ActionClass] = frozenset(
    {"write", "delete", "deploy", "mutate", "side_effect"}
)


@dataclass
class ResourceACLDecision:
    allowed: bool
    reason: str = "ok"
    service: str | None = None
    kind: str | None = None
    action: ActionClass = "read"
    resource_id: str | None = None
    extraction: dict[str, Any] | None = None
    actor_type: str | None = None
    actor_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "service": self.service,
            "kind": self.kind,
            "action": self.action,
            "resource_id": self.resource_id,
            "extraction": self.extraction,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
        }


def _normalize_id(value: str) -> str:
    return str(value).lower().replace("#", "").replace("-", "")


def _normalize_path(value: str) -> str:
    return str(value).lower().rstrip("/")


def _id_allowed(resource_id: str, allowed: list[str], *, prefix: bool) -> bool:
    if prefix:
        ref = _normalize_path(resource_id)
        for item in allowed:
            prefix_val = _normalize_path(item)
            if ref == prefix_val or ref.startswith(prefix_val + "/"):
                return True
        return False
    allowed_set = {_normalize_id(item) for item in allowed}
    return _normalize_id(resource_id) in allowed_set


def _kind_match_mode(service: str, kind: str) -> str:
    spec = SERVICE_RESOURCE_REGISTRY.get(service)
    if not spec:
        return "exact"
    for item in spec.kinds:
        if item.kind == kind:
            return item.match_mode
    return "exact"


def enforce_service_resources(
    restrictions: dict[str, list[str]],
    extraction: ExtractionResult,
    *,
    fail_closed_on_indeterminate: bool | None = None,
) -> ResourceACLDecision:
    """Enforce {kind: [ids]} restrictions for one service against an extraction."""
    if not restrictions:
        return ResourceACLDecision(
            allowed=True,
            reason="unrestricted",
            service=extraction.service,
            action=extraction.action,
            extraction=extraction.to_dict(),
        )

    active = {k: v for k, v in restrictions.items() if isinstance(v, list) and v}
    if not active:
        return ResourceACLDecision(
            allowed=True,
            reason="unrestricted",
            service=extraction.service,
            action=extraction.action,
            extraction=extraction.to_dict(),
        )

    close_indeterminate = (
        fail_closed_on_indeterminate
        if fail_closed_on_indeterminate is not None
        else extraction.action in FAIL_CLOSED_ACTIONS
    )

    for kind, allowed_ids in active.items():
        if kind in extraction.indeterminate_kinds:
            if close_indeterminate:
                return ResourceACLDecision(
                    allowed=False,
                    reason="indeterminate_write_target",
                    service=extraction.service,
                    kind=kind,
                    action=extraction.action,
                    extraction=extraction.to_dict(),
                )
            # Read policy: less restrictive; allow when id cannot be determined.
            continue

        prefix = _kind_match_mode(extraction.service or "", kind) == "prefix"
        for ref in extraction.refs:
            if ref.kind != kind:
                continue
            if not _id_allowed(ref.resource_id, allowed_ids, prefix=prefix):
                return ResourceACLDecision(
                    allowed=False,
                    reason="resource_not_granted",
                    service=extraction.service,
                    kind=kind,
                    action=extraction.action,
                    resource_id=ref.resource_id,
                    extraction=extraction.to_dict(),
                )

    return ResourceACLDecision(
        allowed=True,
        reason="ok",
        service=extraction.service,
        action=extraction.action,
        extraction=extraction.to_dict(),
    )


def check_resource_acl(
    tool_name: str,
    args: dict[str, Any] | None,
    *,
    actor_type: ActorType | None = None,
    actor_id: str | None = None,
    store: ResourceGrantStore | None = None,
) -> ResourceACLDecision:
    """Check resource ACL for a tool call.

    No actor / no grants for the service => unrestricted (legacy broad access).
    Non-empty grants for a service => enforce those kinds.
    """
    extraction = extract_resources(tool_name, args)
    if extraction.service is None:
        return ResourceACLDecision(
            allowed=True,
            reason="no_service_mapping",
            action=extraction.action,
            extraction=extraction.to_dict(),
            actor_type=actor_type,
            actor_id=actor_id,
        )

    if not actor_type or not actor_id:
        # Fail closed for dangerous actions without an actor identity when
        # KEPRIX_RESOURCE_ACL_REQUIRE_ACTOR is set; otherwise allow (local CE).
        import os

        require = (os.environ.get("KEPRIX_RESOURCE_ACL_REQUIRE_ACTOR") or "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        if require and extraction.action in FAIL_CLOSED_ACTIONS:
            return ResourceACLDecision(
                allowed=False,
                reason="actor_required",
                service=extraction.service,
                action=extraction.action,
                extraction=extraction.to_dict(),
            )
        return ResourceACLDecision(
            allowed=True,
            reason="no_actor_unrestricted",
            service=extraction.service,
            action=extraction.action,
            extraction=extraction.to_dict(),
        )

    grant_store = store or get_resource_grant_store()
    try:
        grouped = grant_store.service_resources(actor_type, actor_id)
    except Exception:
        logger.exception("resource grant store read failed open")
        return ResourceACLDecision(
            allowed=True,
            reason="store_unavailable",
            service=extraction.service,
            action=extraction.action,
            extraction=extraction.to_dict(),
            actor_type=actor_type,
            actor_id=actor_id,
        )

    restrictions = grouped.get(extraction.service) or {}
    decision = enforce_service_resources(restrictions, extraction)
    decision.actor_type = actor_type
    decision.actor_id = actor_id
    return decision


async def check_and_audit_resource_acl(
    tool_name: str,
    args: dict[str, Any] | None,
    *,
    product_id: str = "keprix",
    actor_type: ActorType | None = None,
    actor_id: str | None = None,
    workspace_id: str | None = None,
    session_id: str | None = None,
    store: ResourceGrantStore | None = None,
) -> ResourceACLDecision:
    decision = check_resource_acl(
        tool_name,
        args,
        actor_type=actor_type,
        actor_id=actor_id,
        store=store,
    )
    try:
        from keprix.security.tool_acl import ACLDecision
        from keprix.security.tool_acl_audit import get_acl_audit_log

        await get_acl_audit_log().record(
            product_id=product_id,
            tool_name=tool_name,
            decision=ACLDecision.ALLOWED if decision.allowed else ACLDecision.DENIED,
            workspace_id=workspace_id,
            session_id=session_id,
            action=decision.action,
            service=decision.service,
            resource_kind=decision.kind,
            resource_id=decision.resource_id,
            actor_type=decision.actor_type,
            actor_id=decision.actor_id,
            reason=decision.reason,
            policy_decision=decision.to_dict(),
        )
    except Exception:
        logger.debug("resource ACL audit failed", exc_info=True)

    if not decision.allowed:
        try:
            from keprix.security.audit import audit_log

            await audit_log(
                "resource_acl_denied",
                user_id=actor_id if actor_type == "user" else None,
                event_data={
                    "tool": tool_name,
                    "action": decision.action,
                    "service": decision.service,
                    "kind": decision.kind,
                    "resource_id": decision.resource_id,
                    "workspace_id": workspace_id,
                    "actor_type": actor_type,
                    "actor_id": actor_id,
                    "reason": decision.reason,
                    "policy": decision.to_dict(),
                },
                severity="warning",
            )
        except Exception:
            logger.debug("resource_acl_denied audit_log failed", exc_info=True)
    return decision
