"""Create user skills from approved Agent OS proposals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from keprix.improvement.skill_proposer import SkillProposal, SkillProposalStore
from keprix_constants import get_keprix_home


def render_skill_md(proposal: SkillProposal) -> str:
    frontmatter = {
        "name": proposal.slug,
        "description": proposal.description[:1024],
        "version": "0.1.0",
        "metadata": {
            "keprix": {
                "source": "agent-os",
                "proposal_id": proposal.proposal_id,
                "tags": ["agent-os", "workflow-audit"],
            }
        },
    }
    body = f"""# {proposal.name}

Use this skill when the operator needs to repeat this workflow:

{proposal.description}

## Inputs

- Current request or source material from the operator
- Relevant workspace files, notes, or session context

## Procedure

1. Clarify the expected output only when it is ambiguous.
2. Gather the required context from available Keprix tools.
3. Produce the requested output in a reusable, reviewable format.
4. Note any missing credentials, files, or approvals before taking external action.

## Evidence

- Source: {proposal.source}
- Sessions: {", ".join(proposal.evidence_sessions) if proposal.evidence_sessions else "none recorded"}
- Tools observed: {", ".join(proposal.tools_used) if proposal.tools_used else "none recorded"}
"""
    return f"---\n{yaml.safe_dump(frontmatter, sort_keys=False).strip()}\n---\n\n{body}"


def package_skill(proposal_id: str, *, store: SkillProposalStore | None = None) -> SkillProposal:
    store = store or SkillProposalStore()
    proposal = store.get(proposal_id)
    if proposal is None:
        raise KeyError(proposal_id)
    if proposal.status not in {"pending", "approved"}:
        raise ValueError(f"Cannot approve proposal with status {proposal.status}")
    skill_dir = get_keprix_home() / "skills" / proposal.slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(render_skill_md(proposal), encoding="utf-8")
    (skill_dir / "references").mkdir(exist_ok=True)
    (skill_dir / "references" / "proposal.json").write_text(json.dumps(proposal.to_dict(), indent=2), encoding="utf-8")
    proposal.status = "approved"
    proposal.skill_path = str(skill_dir)
    return store.save(proposal)
