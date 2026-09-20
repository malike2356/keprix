"""Propose / approve / deny mutation mounts via reversible lifecycle (769)."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from keprix.mutation.mount.banned import MountBanError, assert_mount_allowed, banned_summary
from keprix.mutation.mount.intents import (
    MountIntent,
    map_legacy_mutation_to_intent,
    mutation_ledger_id,
    skill_plugin_id,
)
from keprix.mutation.mount.store import (
    MountProposal,
    MountProposalStore,
    get_mount_proposal_store,
    reset_mount_proposal_store_for_tests,
)

logger = logging.getLogger(__name__)


class MountApprovalError(PermissionError):
    """Human approval / four-eyes failure."""


class MountApplyError(RuntimeError):
    """Apply failed after approval."""


def _record_trajectory(
    trajectory_id: str | None,
    stage: str,
    detail: dict[str, Any],
    *,
    error_text: str | None = None,
) -> None:
    if not trajectory_id:
        return
    try:
        from keprix.trajectory.service import get_trajectory_service

        get_trajectory_service().record_mutation(
            trajectory_id,
            stage=stage,
            detail=detail,
            error_text=error_text,
        )
    except Exception as exc:
        logger.debug("trajectory mutation record skipped: %s", exc)


def _ensure_plugin_stub(plugin_id: str) -> Any:
    from keprix_cli.plugins import LoadedPlugin, PluginManifest, get_plugin_manager

    mgr = get_plugin_manager()
    if not getattr(mgr, "_discovered", False):
        mgr._discovered = True
    if plugin_id not in mgr._plugins:
        manifest = PluginManifest(
            name=plugin_id,
            key=plugin_id,
            source="user",
            kind="standalone",
        )
        mgr._plugins[plugin_id] = LoadedPlugin(manifest=manifest, enabled=True)
    else:
        mgr._plugins[plugin_id].enabled = True
    return mgr


def _register_declared_tools(plugin_id: str, tools: list[dict[str, Any]]) -> list[str]:
    from keprix_cli.plugins import PluginContext

    mgr = _ensure_plugin_stub(plugin_id)
    loaded = mgr._plugins[plugin_id]
    ctx = PluginContext(loaded.manifest, mgr)
    mounted: list[str] = []
    for tool in tools:
        name = str(tool.get("name") or "").strip()
        if not name:
            continue

        def _handler(args, _name=name, **kwargs):
            return f'{{"ok": true, "mutation_mount_tool": "{_name}"}}'

        ctx.register_tool(
            name=name,
            toolset="mutation_mount",
            schema={
                "name": name,
                "description": tool.get("description") or f"mutation mount {name}",
                "parameters": tool.get("parameters") or {},
            },
            handler=_handler,
            description=tool.get("description") or f"mutation mount {name}",
        )
        mounted.append(name)
    return mounted


def _apply_intent(proposal: MountProposal, *, who: str) -> dict[str, Any]:
    from keprix.plugin_lifecycle import (
        disable_plugin_hot,
        enable_plugin_hot,
        get_lifecycle_ledger,
        unmount_plugin,
    )

    intent = proposal.intent
    action = intent.action
    result: dict[str, Any] = {"action": action, "who": who}

    if action == "mount_plugin":
        plugin_id = intent.target_id
        _ensure_plugin_stub(plugin_id)
        declared = list(intent.declared_tools or [])
        if declared:
            # Prefer reversible declared tools under the real plugin id.
            unmount_plugin(plugin_id, who=who)
            tools = _register_declared_tools(plugin_id, declared)
            result["lifecycle"] = {
                "ok": True,
                "plugin_id": plugin_id,
                "action": "mount",
                "declared_tools": tools,
            }
            result["ledger"] = (get_lifecycle_ledger().get(plugin_id) or None)
            if result["ledger"] is not None:
                result["ledger"] = result["ledger"].snapshot()
        else:
            result["lifecycle"] = enable_plugin_hot(plugin_id, who=who)
        result["ledger_plugin_id"] = plugin_id

    elif action == "unmount_plugin":
        result["lifecycle"] = disable_plugin_hot(intent.target_id, who=who)
        result["ledger_plugin_id"] = intent.target_id

    elif action == "mount_skill":
        plugin_id = skill_plugin_id(intent.target_id)
        _ensure_plugin_stub(plugin_id)
        tools = intent.declared_tools or [
            {
                "name": f"skill_marker_{intent.target_id.replace(':', '_').replace('/', '_')}",
                "description": f"skill mount marker for {intent.target_id}",
            }
        ]
        unmount_plugin(plugin_id, who=who)
        mounted = _register_declared_tools(plugin_id, tools)
        from keprix.plugin_lifecycle.ledger import get_lifecycle_ledger as _gl

        _gl().record_skill(plugin_id, intent.target_id)
        result["lifecycle"] = {
            "ok": True,
            "plugin_id": plugin_id,
            "action": "mount_skill",
            "declared_tools": mounted,
            "skill": intent.target_id,
        }
        result["ledger_plugin_id"] = plugin_id

    elif action == "unmount_skill":
        plugin_id = skill_plugin_id(intent.target_id)
        result["lifecycle"] = disable_plugin_hot(plugin_id, who=who)
        result["ledger_plugin_id"] = plugin_id

    elif action == "swap_provider":
        from keprix.plugin_lifecycle.ledger import get_lifecycle_ledger
        from keprix.seams.bootstrap import ensure_default_seams
        from keprix.seams.registry import get_seam_registry

        ensure_default_seams()
        registry = get_seam_registry()
        seam = str(intent.seam or "")
        provider_id = str(intent.provider_id or "")
        available = registry.list_providers(seam)  # type: ignore[arg-type]
        if provider_id not in available:
            raise MountApplyError(
                f"unknown provider {provider_id!r} for seam {seam}; available={available}"
            )
        previous = registry.active_id(seam)  # type: ignore[arg-type]
        registry.set_active(seam, provider_id)  # type: ignore[arg-type]
        ledger_id = mutation_ledger_id(proposal.id)
        get_lifecycle_ledger().record_seam_provider(ledger_id, seam, provider_id)
        result["lifecycle"] = {
            "ok": True,
            "action": "swap_provider",
            "seam": seam,
            "provider_id": provider_id,
            "previous_provider_id": previous,
            "ledger_plugin_id": ledger_id,
        }
        result["ledger_plugin_id"] = ledger_id
        # Persist previous for reverse.
        intent.previous_provider_id = previous
    else:
        raise MountApplyError(f"unsupported action {action}")

    return result


def _reverse_intent(proposal: MountProposal, *, who: str) -> dict[str, Any]:
    from keprix.plugin_lifecycle import disable_plugin_hot, enable_plugin_hot, unmount_plugin

    intent = proposal.intent
    action = intent.action
    if action in {"mount_plugin", "mount_skill"}:
        plugin_id = (
            skill_plugin_id(intent.target_id)
            if action == "mount_skill"
            else intent.target_id
        )
        return {"lifecycle": disable_plugin_hot(plugin_id, who=who), "reversed": True}
    if action in {"unmount_plugin", "unmount_skill"}:
        plugin_id = (
            skill_plugin_id(intent.target_id)
            if action == "unmount_skill"
            else intent.target_id
        )
        return {"lifecycle": enable_plugin_hot(plugin_id, who=who), "reversed": True}
    if action == "swap_provider":
        from keprix.seams.registry import get_seam_registry

        prev = intent.previous_provider_id
        if not prev:
            raise MountApplyError("no previous_provider_id to restore")
        get_seam_registry().set_active(str(intent.seam), prev)  # type: ignore[arg-type]
        unmount_plugin(mutation_ledger_id(proposal.id), who=who)
        return {
            "lifecycle": {
                "ok": True,
                "restored_provider_id": prev,
                "seam": intent.seam,
            },
            "reversed": True,
        }
    raise MountApplyError(f"cannot reverse action {action}")


class MutationMountService:
    """Human-gated mount/unmount proposals backed by 769."""

    def __init__(self, store: MountProposalStore | None = None) -> None:
        self._store = store or get_mount_proposal_store()

    @property
    def store(self) -> MountProposalStore:
        return self._store

    def propose(
        self,
        intent: MountIntent | dict[str, Any],
        *,
        proposed_by: str,
        workspace_id: str = "default",
        trajectory_id: str | None = None,
    ) -> MountProposal:
        if isinstance(intent, dict):
            intent = MountIntent.from_dict(intent)
        assert_mount_allowed(
            action=intent.action,
            target_id=intent.target_id,
            seam=intent.seam,
            provider_id=intent.provider_id,
            metadata=intent.metadata,
        )
        proposal = self._store.create(
            intent=intent,
            proposed_by=proposed_by,
            workspace_id=workspace_id,
            trajectory_id=trajectory_id,
        )
        _record_trajectory(
            trajectory_id or proposal.trajectory_id,
            "propose",
            {
                "kind": "mount",
                "proposal_id": proposal.id,
                "action": intent.action,
                "target_id": intent.target_id,
                "applied": False,
            },
        )
        return proposal

    def propose_from_kind(
        self,
        *,
        kind: str,
        name: str,
        proposed_by: str,
        detail: dict[str, Any] | None = None,
        workspace_id: str = "default",
        trajectory_id: str | None = None,
    ) -> MountProposal:
        intent = map_legacy_mutation_to_intent(kind=kind, name=name, detail=detail)
        return self.propose(
            intent,
            proposed_by=proposed_by,
            workspace_id=workspace_id,
            trajectory_id=trajectory_id,
        )

    def deny(
        self,
        proposal_id: str,
        *,
        denied_by: str,
        reason: str = "",
    ) -> MountProposal:
        proposal = self._store.get(proposal_id)
        if proposal is None:
            raise KeyError(f"unknown proposal {proposal_id}")
        if proposal.status not in {"proposed"}:
            raise MountApprovalError(f"cannot deny proposal in status {proposal.status}")
        # Snapshot ledger before deny to prove unchanged after.
        from keprix.plugin_lifecycle import get_lifecycle_ledger

        before = get_lifecycle_ledger().snapshot()
        updated = self._store.update(
            proposal_id,
            status="denied",
            denied_by=denied_by,
            deny_reason=reason,
        )
        after = get_lifecycle_ledger().snapshot()
        if before != after:
            logger.error("deny path mutated ledger unexpectedly for %s", proposal_id)
        _record_trajectory(
            proposal.trajectory_id,
            "deny",
            {
                "kind": "mount",
                "proposal_id": proposal_id,
                "action": proposal.action,
                "target_id": proposal.target_id,
                "applied": False,
                "denied_by": denied_by,
                "reason": reason,
            },
        )
        assert updated is not None
        return updated

    def approve(
        self,
        proposal_id: str,
        *,
        approved_by: str,
        allow_same_actor: bool = False,
    ) -> MountProposal:
        """Approve and apply via 769. Four-eyes: approved_by != proposed_by."""
        proposal = self._store.get(proposal_id)
        if proposal is None:
            raise KeyError(f"unknown proposal {proposal_id}")
        if proposal.status != "proposed":
            raise MountApprovalError(
                f"cannot approve proposal in status {proposal.status}"
            )
        if not approved_by or not approved_by.strip():
            raise MountApprovalError("approved_by is required (human approval)")
        if (
            not allow_same_actor
            and approved_by.strip().lower() == proposal.proposed_by.strip().lower()
        ):
            raise MountApprovalError(
                "four-eyes required: approved_by must differ from proposed_by"
            )

        # Re-check bans at apply time.
        assert_mount_allowed(
            action=proposal.intent.action,
            target_id=proposal.intent.target_id,
            seam=proposal.intent.seam,
            provider_id=proposal.intent.provider_id,
            metadata=proposal.intent.metadata,
        )

        _record_trajectory(
            proposal.trajectory_id,
            "approve",
            {
                "kind": "mount",
                "proposal_id": proposal_id,
                "action": proposal.action,
                "target_id": proposal.target_id,
                "approved_by": approved_by,
            },
        )

        apply_result = _apply_intent(proposal, who=approved_by)
        terminal = (
            "unmounted"
            if proposal.action in {"unmount_plugin", "unmount_skill"}
            else "mounted"
        )
        self._store.update(
            proposal_id,
            status=terminal,
            approved_by=approved_by,
            apply_result=apply_result,
        )
        if proposal.action == "swap_provider" and proposal.intent.previous_provider_id:
            import json

            with self._store._lock:
                conn = self._store._conn()
                try:
                    row = conn.execute(
                        "SELECT intent_json FROM mutation_mount_proposals WHERE id = ?",
                        (proposal_id,),
                    ).fetchone()
                    intent_data = json.loads(row["intent_json"])
                    intent_data["previous_provider_id"] = (
                        proposal.intent.previous_provider_id
                    )
                    conn.execute(
                        "UPDATE mutation_mount_proposals SET intent_json = ? WHERE id = ?",
                        (json.dumps(intent_data, ensure_ascii=False), proposal_id),
                    )
                    conn.commit()
                finally:
                    conn.close()

        stage = (
            "unmount"
            if proposal.action in {"unmount_plugin", "unmount_skill"}
            else "mount"
        )
        _record_trajectory(
            proposal.trajectory_id,
            stage,
            {
                "kind": "mount",
                "proposal_id": proposal_id,
                "action": proposal.action,
                "target_id": proposal.target_id,
                "applied": True,
                "apply_result": {
                    k: v for k, v in apply_result.items() if k != "ledger"
                },
            },
        )
        updated = self._store.get(proposal_id)
        assert updated is not None
        return updated

    def reverse(self, proposal_id: str, *, who: str) -> MountProposal:
        proposal = self._store.get(proposal_id)
        if proposal is None:
            raise KeyError(f"unknown proposal {proposal_id}")
        if proposal.status not in {"mounted", "unmounted"}:
            raise MountApprovalError(
                f"cannot reverse proposal in status {proposal.status}"
            )
        result = _reverse_intent(proposal, who=who)
        updated = self._store.update(
            proposal_id,
            status="reversed",
            apply_result={**(proposal.apply_result or {}), "reverse": result},
        )
        _record_trajectory(
            proposal.trajectory_id,
            "unmount" if proposal.status == "mounted" else "mount",
            {
                "kind": "mount",
                "proposal_id": proposal_id,
                "reversed": True,
                "who": who,
            },
        )
        assert updated is not None
        return updated


_SERVICE: MutationMountService | None = None
_SERVICE_LOCK = threading.Lock()


def get_mutation_mount_service(
    store: MountProposalStore | None = None,
) -> MutationMountService:
    global _SERVICE
    if store is not None:
        return MutationMountService(store=store)
    with _SERVICE_LOCK:
        if _SERVICE is None:
            _SERVICE = MutationMountService()
        return _SERVICE


def reset_mutation_mount_service_for_tests(
    sqlite_path: Path | None = None,
) -> MutationMountService:
    global _SERVICE
    store = reset_mount_proposal_store_for_tests(sqlite_path=sqlite_path)
    with _SERVICE_LOCK:
        _SERVICE = MutationMountService(store=store)
        return _SERVICE


__all__ = [
    "MountApprovalError",
    "MountApplyError",
    "MountBanError",
    "MutationMountService",
    "banned_summary",
    "get_mutation_mount_service",
    "reset_mutation_mount_service_for_tests",
]
