"""Persistent Agent OS onboarding checklist progress."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from keprix.agent_os.onboarding_steps import STEP_BY_ID, STEPS, all_step_ids, steps_payload
from keprix_constants import get_keprix_home


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_user_id(user_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in str(user_id or "default"))
    return cleaned or "default"


def onboarding_path(user_id: str) -> Path:
    path = get_keprix_home() / "users" / _safe_user_id(user_id) / "agent-os-onboarding.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class OnboardingProgress:
    user_id: str
    steps: dict[str, bool]
    completed_at: str | None = None
    dismissed: bool = False

    @property
    def onboarding_completed(self) -> bool:
        return self.completed_at is not None

    @property
    def pending_count(self) -> int:
        return sum(1 for done in self.steps.values() if not done)

    @property
    def completed_count(self) -> int:
        return sum(1 for done in self.steps.values() if done)

    def normalize(self) -> None:
        known = set(all_step_ids())
        self.steps = {step_id: bool(self.steps.get(step_id, False)) for step_id in all_step_ids()}
        for stale in set(self.steps) - known:
            self.steps.pop(stale, None)
        self.completed_at = self.completed_at or (_now() if self.steps and all(self.steps.values()) else None)

    def reconcile_local_state(self) -> None:
        """Backfill checklist progress from local Agent OS artifacts.

        Older builds did not emit every onboarding event. This keeps the
        checklist honest after upgrades without marking steps that have no
        concrete local evidence.
        """

        detected = _detect_completed_steps(self.user_id)
        for step_id in detected:
            if step_id in STEP_BY_ID:
                self.steps[step_id] = True

    def to_dict(self) -> dict[str, Any]:
        self.normalize()
        activation_ids = {step.id for step in STEPS if step.track == "activation"}
        activation_done = all(self.steps.get(step_id) for step_id in activation_ids) if activation_ids else True
        next_activation = next(
            (step for step in STEPS if step.track == "activation" and not self.steps.get(step.id)),
            None,
        )
        return {
            "user_id": self.user_id,
            "steps": self.steps,
            "step_definitions": steps_payload(),
            "completed_at": self.completed_at,
            "dismissed": self.dismissed,
            "onboarding_completed": self.onboarding_completed,
            "pending_count": self.pending_count,
            "completed_count": self.completed_count,
            "total_count": len(self.steps),
            "banner_visible": not self.dismissed and not activation_done,
            "activation_completed": activation_done,
            "next_activation": next_activation.to_dict() if next_activation else None,
        }

    @classmethod
    def from_dict(cls, user_id: str, data: dict[str, Any] | None) -> "OnboardingProgress":
        progress = cls(
            user_id=user_id,
            steps=dict((data or {}).get("steps") or {}),
            completed_at=(data or {}).get("completed_at"),
            dismissed=bool((data or {}).get("dismissed", False)),
        )
        progress.normalize()
        return progress


class OnboardingProgressStore:
    def load(self, user_id: str) -> OnboardingProgress:
        path = onboarding_path(user_id)
        if not path.is_file():
            progress = OnboardingProgress.from_dict(user_id, None)
        else:
            progress = OnboardingProgress.from_dict(user_id, json.loads(path.read_text(encoding="utf-8")))
        before = dict(progress.steps)
        progress.reconcile_local_state()
        progress.normalize()
        if progress.steps != before:
            self.save(progress)
        return progress

    def save(self, progress: OnboardingProgress) -> OnboardingProgress:
        progress.normalize()
        onboarding_path(progress.user_id).write_text(json.dumps(progress.to_dict(), indent=2), encoding="utf-8")
        return progress

    def complete_step(self, user_id: str, step_id: str) -> OnboardingProgress:
        if step_id not in STEP_BY_ID:
            raise KeyError(step_id)
        progress = self.load(user_id)
        progress.steps[step_id] = True
        progress.normalize()
        return self.save(progress)

    def complete_all(self, user_id: str) -> OnboardingProgress:
        progress = self.load(user_id)
        for step_id in all_step_ids():
            progress.steps[step_id] = True
        progress.normalize()
        return self.save(progress)

    def dismiss(self, user_id: str, dismissed: bool = True) -> OnboardingProgress:
        progress = self.load(user_id)
        progress.dismissed = dismissed
        return self.save(progress)

    def reset(self, user_id: str) -> OnboardingProgress:
        progress = OnboardingProgress.from_dict(user_id, None)
        return self.save(progress)


def _detect_completed_steps(user_id: str) -> set[str]:
    completed: set[str] = set()

    # Activation: provider configured (instance setup), not the interview.
    try:
        from keprix.setup.status import provider_configured

        if provider_configured() or os.environ.get("KEPRIX_SETUP_COMPLETE", "").strip().lower() in {"1", "true", "yes"}:
            completed.add("a1_provider")
    except Exception:
        if os.environ.get("KEPRIX_SETUP_COMPLETE", "").strip().lower() in {"1", "true", "yes"}:
            completed.add("a1_provider")

    try:
        from keprix_constants import get_keprix_home

        sessions_dir = get_keprix_home() / "sessions"
        if sessions_dir.is_dir() and any(sessions_dir.rglob("*.json")):
            completed.add("a2_first_chat")
    except Exception:
        pass

    try:
        from keprix.setup.status import channel_configured

        if channel_configured():
            completed.add("a3_channel")
    except Exception:
        pass

    try:
        from keprix.agent_os.audit_store import AuditStore

        if any(audit.status == "completed" for audit in AuditStore().list_audits(user_id=user_id)):
            completed.add("l1_audit")
    except Exception:
        pass

    try:
        from keprix.agent_os.audit_store import _proposals_queue_path

        path = _proposals_queue_path()
        if path.is_file():
            proposals = json.loads(path.read_text(encoding="utf-8"))
            if any(str(item.get("status") or "").lower() in {"approved", "active"} for item in proposals):
                completed.add("l1_first_skill")
    except Exception:
        pass

    try:
        from keprix.agent_os.automation_link_store import AutomationLinkStore

        if AutomationLinkStore().list():
            completed.add("l1_promote")
    except Exception:
        pass

    try:
        from keprix.agent_os.run_ledger_store import RunLedgerStore

        ledger = RunLedgerStore()
        if any(profile.baseline_entry_ids for profile in _list_loop_profiles()):
            completed.add("l1_baseline")
        if ledger.list(limit=1):
            completed.add("l3_headless")
    except Exception:
        pass

    try:
        from keprix.workspace.template_presets import workspace_root

        if workspace_root("personal-os").exists():
            completed.add("l2_workspace")
    except Exception:
        pass

    try:
        from keprix.vault.config import get_vault_config

        vault = get_vault_config()
        if vault.root_path and Path(vault.root_path).expanduser().exists():
            completed.add("l2_vault")
            if any(Path(vault.root_path).expanduser().rglob("*.md")):
                completed.add("l2_wiki")
    except Exception:
        pass

    try:
        from keprix.agent_os.connections_service import ConnectionsService

        domains = ConnectionsService().load(workspace_id="personal-os")
        if any(domain.status == "live" for domain in domains):
            completed.add("l2_connect_one")
    except Exception:
        pass

    try:
        from keprix.agent_os.maturity_audit_service import MaturityAuditService

        if MaturityAuditService().list(limit=1):
            completed.add("l2_four_cs_audit")
    except Exception:
        pass

    try:
        from keprix.agent_os.action_board_store import ActionBoardStore

        if ActionBoardStore().load(user_id).pins:
            completed.add("l3_pin")
    except Exception:
        pass

    try:
        from keprix_constants import get_keprix_home

        if (get_keprix_home() / "cron" / "jobs.json").is_file():
            completed.add("l3_schedule")
        if any((get_keprix_home() / "agent-os").glob("*client*kit*.zip")):
            completed.add("l4_kit")
    except Exception:
        pass

    return completed


def _list_loop_profiles() -> list[Any]:
    try:
        from keprix.agent_os.run_ledger_store import _profiles_dir
        from keprix.agent_os.run_ledger import LoopProfile

        profiles = []
        for path in _profiles_dir().glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            profiles.append(
                LoopProfile(
                    source_type=str(data["source_type"]),
                    source_id=str(data["source_id"]),
                    baseline_entry_ids=list(data.get("baseline_entry_ids") or []),
                    improvement_proposals=list(data.get("improvement_proposals") or []),
                )
            )
        return profiles
    except Exception:
        return []
