"""Loop profile analysis for Agent OS run drift."""

from __future__ import annotations

from statistics import mean
from typing import Any
from uuid import uuid4

import yaml

from keprix.agent_os.run_ledger import LoopProfile, utc_now_iso
from keprix.agent_os.run_ledger_store import RunLedgerStore


class LoopProfileEngine:
    def __init__(self, store: RunLedgerStore | None = None) -> None:
        self.store = store or RunLedgerStore()

    def record_baseline(self, source_type: str, source_id: str, entry_ids: list[str] | None = None, *, last_n: int = 5) -> LoopProfile:
        if entry_ids is None:
            entries = [
                entry
                for entry in self.store.list(source_type=source_type, source_id=source_id, status="completed", limit=last_n)
                if entry.eval_score is not None
            ]
            entry_ids = [entry.entry_id for entry in entries[: max(1, min(last_n, 50))]]
        profile = self.store.get_profile(source_type, source_id) or LoopProfile(source_type=source_type, source_id=source_id)
        profile.baseline_entry_ids = list(entry_ids)
        profile.improvement_proposals = self.analyze_drift(source_type, source_id)
        return self.store.save_profile(profile)

    def analyze_drift(self, source_type: str, source_id: str) -> list[dict[str, Any]]:
        profile = self.store.get_profile(source_type, source_id)
        if not profile or not profile.baseline_entry_ids:
            return []
        baseline_entries = [self.store.get(entry_id) for entry_id in profile.baseline_entry_ids]
        baseline = [entry for entry in baseline_entries if entry is not None]
        recent = self.store.list(source_type=source_type, source_id=source_id, limit=10)
        proposals: list[dict[str, Any]] = []
        baseline_scores = [entry.eval_score for entry in baseline if entry.eval_score is not None]
        recent_scores = [entry.eval_score for entry in recent[:3] if entry.eval_score is not None]
        if baseline_scores and recent_scores:
            baseline_avg = mean(baseline_scores)
            recent_avg = mean(recent_scores)
            if baseline_avg and recent_avg < baseline_avg * 0.9:
                proposals.append(
                    self._proposal(
                        source_type,
                        source_id,
                        "eval_drift",
                        "Evaluation score dropped",
                        f"Recent average {recent_avg:.2f} is more than 10% below baseline {baseline_avg:.2f}.",
                        {"baseline_avg": baseline_avg, "recent_avg": recent_avg},
                    )
                )
        baseline_tokens = [entry.tokens for entry in baseline if entry.tokens > 0]
        recent_tokens = [entry.tokens for entry in recent[:3] if entry.tokens > 0]
        if baseline_tokens and recent_tokens and mean(recent_tokens) > mean(baseline_tokens) * 1.25:
            proposals.append(
                self._proposal(
                    source_type,
                    source_id,
                    "token_rise",
                    "Token usage increased",
                    "Recent runs are using at least 25% more tokens than the baseline.",
                    {"baseline_tokens": mean(baseline_tokens), "recent_tokens": mean(recent_tokens)},
                )
            )
        corrections = [correction for entry in recent for correction in entry.user_corrections]
        if len(corrections) >= 2:
            proposals.append(
                self._proposal(
                    source_type,
                    source_id,
                    "user_corrections",
                    "Repeated user corrections",
                    "Recent runs include repeated operator corrections.",
                    {"corrections": corrections[:5]},
                )
            )
        if any((entry.output_summary.get("approval_backlog") or 0) for entry in recent):
            proposals.append(
                self._proposal(
                    source_type,
                    source_id,
                    "approval_backlog",
                    "Approval backlog detected",
                    "One or more runs ended with pending approval work.",
                    {},
                )
            )
        if profile:
            profile.improvement_proposals = proposals
            self.store.save_profile(profile)
        return proposals

    def apply_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        for profile_path in (self.store.get_profile(source_type, source_id) for source_type, source_id in self._profile_keys()):
            if not profile_path:
                continue
            for proposal in profile_path.improvement_proposals:
                if proposal.get("proposal_id") == proposal_id:
                    filename = "skill-patch.md" if profile_path.source_type == "skill" else "playbook-draft.yaml"
                    content = self._draft_content(profile_path.source_type, profile_path.source_id, proposal)
                    path = self.store.write_draft(proposal_id, filename, content)
                    proposal["status"] = "draft_created"
                    proposal["draft_path"] = str(path)
                    self.store.save_profile(profile_path)
                    return {"proposal": proposal, "draft_path": str(path)}
        return None

    def _profile_keys(self) -> list[tuple[str, str]]:
        from keprix.agent_os.run_ledger_store import _profiles_dir

        keys: list[tuple[str, str]] = []
        for path in _profiles_dir().glob("*.json"):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            keys.append((str(data.get("source_type") or ""), str(data.get("source_id") or "")))
        return keys

    def _proposal(self, source_type: str, source_id: str, category: str, title: str, detail: str, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "proposal_id": f"lp_{uuid4().hex}",
            "source_type": source_type,
            "source_id": source_id,
            "category": category,
            "title": title,
            "detail": detail,
            "metadata": metadata,
            "status": "pending_approval",
            "created_at": utc_now_iso(),
        }

    def _draft_content(self, source_type: str, source_id: str, proposal: dict[str, Any]) -> str:
        if source_type == "skill":
            return f"# Skill patch draft for {source_id}\n\n## Proposal\n\n{proposal.get('detail', '')}\n\n## Suggested edit\n\nReview the skill prompt and add clearer success criteria.\n"
        document = {
            "graph_id": f"{source_id}-loop-draft",
            "name": f"{source_id} loop profile draft",
            "steps": [
                {
                    "id": "review-loop-proposal",
                    "type": "agent_task",
                    "config": {
                        "prompt": f"Review loop profile proposal for {source_id}: {proposal.get('detail', '')}",
                    },
                }
            ],
        }
        return yaml.safe_dump(document, sort_keys=False)
