"""Skill run follow-up loop detection."""

from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.improvement.skill_proposer import SkillProposal, SkillProposalStore, slugify
from keprix_constants import get_keprix_home


def _history_path() -> Path:
    path = get_keprix_home() / "agent-os" / "skill-run-history.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class SkillRunRecord:
    run_id: str
    skill_slug: str
    follow_up_action: str
    session_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def record_skill_run(record: SkillRunRecord) -> None:
    path = _history_path()
    rows: list[dict[str, Any]] = []
    if path.is_file():
        rows = json.loads(path.read_text(encoding="utf-8"))
    rows.append(record.to_dict())
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def propose_skill_improvements(*, threshold: int = 3, store: SkillProposalStore | None = None) -> list[SkillProposal]:
    store = store or SkillProposalStore()
    path = _history_path()
    if not path.is_file():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        action = re.sub(r"\s+", " ", str(row.get("follow_up_action") or "").lower()).strip()
        if len(action) < 8:
            continue
        buckets[(str(row.get("skill_slug") or ""), action)].append(row)

    proposals: list[SkillProposal] = []
    existing = {(item.source, item.slug, item.description) for item in store.list()}
    for (skill_slug, action), items in buckets.items():
        if len(items) < threshold:
            continue
        description = f"Improve {skill_slug} to handle follow-up: {action}"
        slug = slugify(description)
        if ("improvement_loop", slug, description) in existing:
            continue
        proposal = SkillProposal(
            proposal_id=str(uuid.uuid4()),
            source="improvement_loop",
            slug=slug,
            name=description[:80],
            description=description,
            evidence_sessions=[str(item.get("session_id")) for item in items if item.get("session_id")],
            occurrence_count=len(items),
            confidence=0.8,
            rationale=f"Same follow-up action appeared {len(items)} times after skill runs.",
        )
        proposals.append(store.save(proposal))
    return proposals
