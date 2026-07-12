"""Auto-skill writer: successful workflows become reusable skills (Prompt 270 Task 2.5)."""

from __future__ import annotations

import os
import uuid
from typing import Any

from keprix.improvement.skill_packager import package_skill, render_skill_md
from keprix.improvement.skill_proposer import SkillProposal, SkillProposalStore, slugify


def auto_skill_write_enabled() -> bool:
    raw = os.getenv("KEPRIX_AUTO_SKILL_WRITE", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def auto_skill_approve_enabled() -> bool:
    raw = os.getenv("KEPRIX_AUTO_SKILL_APPROVE", "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def write_skill_from_workflow(
    *,
    workflow: str,
    summary: str,
    procedure: str = "",
    tools_used: list[str] | None = None,
    evidence_sessions: list[str] | None = None,
    confidence: float = 0.85,
    store: SkillProposalStore | None = None,
) -> dict[str, Any]:
    """Create a skill proposal (and optionally package it) from a successful run."""
    if not auto_skill_write_enabled():
        return {"ok": False, "skipped": True, "reason": "auto_skill_write_disabled"}

    store = store or SkillProposalStore()
    name = f"{workflow.replace('-', ' ').title()} skill"
    description = (summary or f"Reusable workflow skill for {workflow}").strip()
    body = (procedure or description).strip()
    proposal = SkillProposal(
        proposal_id=str(uuid.uuid4()),
        source="auto_skill_writer",
        slug=slugify(f"{workflow}-{description[:40]}"),
        name=name[:80],
        description=description[:1024],
        evidence_sessions=list(evidence_sessions or []),
        tools_used=list(tools_used or [workflow]),
        occurrence_count=1,
        confidence=confidence,
        status="pending",
        rationale=f"Auto-written after successful `{workflow}` run.\n\n{body}",
    )
    store.save(proposal)

    packaged: dict[str, Any] | None = None
    if auto_skill_approve_enabled():
        approved = package_skill(proposal.proposal_id, store=store)
        packaged = {
            "proposal_id": approved.proposal_id,
            "slug": approved.slug,
            "skill_path": approved.skill_path,
            "status": approved.status,
        }

    preview = render_skill_md(proposal)
    return {
        "ok": True,
        "proposal_id": proposal.proposal_id,
        "slug": proposal.slug,
        "status": proposal.status if not packaged else "approved",
        "packaged": packaged,
        "preview": preview[:2000],
    }


def maybe_write_skill_from_app_run(
    *,
    app_name: str,
    result: dict[str, Any],
    trace_id: str | None = None,
) -> dict[str, Any] | None:
    """Hook used by agent-app runner after a successful run."""
    if not auto_skill_write_enabled():
        return None
    if str(result.get("status") or "ok").lower() not in {"ok", "success"}:
        return None
    workflow = str(result.get("workflow") or app_name)
    # Only auto-write for known Phase 2 workflows / tagged apps.
    allow = {
        "content-series",
        "crm-import",
        "memory-system",
        "hello-agent",
        "hello-world",
        "video-agent",
        "seo-agent",
        "outreach-agent",
        "onboarding-path",
        "error-paste",
    }
    if workflow not in allow and app_name not in allow:
        meta = result.get("artifact") if isinstance(result.get("artifact"), dict) else {}
        if not meta.get("auto_skill"):
            return None

    summary = str(result.get("output") or result.get("artifact") or workflow)[:500]
    procedure = ""
    if isinstance(result.get("steps"), list):
        procedure = "\n".join(
            f"{idx}. {step.get('title') or step}"
            for idx, step in enumerate(result["steps"], start=1)
            if isinstance(step, dict) or isinstance(step, str)
        )
    return write_skill_from_workflow(
        workflow=workflow,
        summary=summary,
        procedure=procedure or summary,
        tools_used=[app_name, workflow],
        evidence_sessions=[trace_id] if trace_id else [],
    )
