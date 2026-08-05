"""Weekly Agent OS skill proposal review report."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.improvement.skill_proposer import SkillProposalStore
from keprix_constants import get_keprix_home


def _reports_dir() -> Path:
    path = get_keprix_home() / "agent-os" / "skill-review"
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_weekly_review(store: SkillProposalStore | None = None) -> dict[str, Any]:
    store = store or SkillProposalStore()
    proposals = store.list()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pending": [item.to_dict() for item in proposals if item.status == "pending"],
        "approved": [item.to_dict() for item in proposals if item.status == "approved"],
        "rejected": [item.to_dict() for item in proposals if item.status == "rejected"],
    }
    path = _reports_dir() / "latest.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def latest_review() -> dict[str, Any]:
    path = _reports_dir() / "latest.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return generate_weekly_review()
