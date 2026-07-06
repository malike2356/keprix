"""Propose prompt improvements from analyzed runs."""

from __future__ import annotations

from dataclasses import dataclass

from keprix.improvement.run_analyzer import ImprovementProposal, RunRecord


@dataclass
class PromptImprovement:
    proposal_id: str
    current_prompt_hint: str
    suggested_prompt: str
    rationale: str


def propose_prompt_improvements(record: RunRecord, proposals: list[ImprovementProposal]) -> list[PromptImprovement]:
    improvements: list[PromptImprovement] = []
    for proposal in proposals:
        if proposal.category not in {"repeated_failure", "user_correction", "low_eval"}:
            continue
        suggested = _suggest_prompt(record, proposal)
        improvements.append(
            PromptImprovement(
                proposal_id=proposal.proposal_id,
                current_prompt_hint=record.metadata.get("persona_id", "default"),
                suggested_prompt=suggested,
                rationale=proposal.detail,
            )
        )
    return improvements


def _suggest_prompt(record: RunRecord, proposal: ImprovementProposal) -> str:
    base = record.metadata.get("system_prompt", "You are a helpful Keprix agent.")
    if proposal.category == "user_correction":
        return base + "\n\nWhen the user corrects you, acknowledge the correction and apply it immediately."
    if proposal.category == "low_eval":
        return base + "\n\nVerify outputs against the requested format before responding."
    return base + "\n\nIf a tool fails, explain the failure and try an alternate approach before giving up."
