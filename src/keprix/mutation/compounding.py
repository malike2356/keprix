"""Deployment mutation compounding metrics (Prompt 154)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from keprix.mutation.store import MutationRecord, get_mutation_store

_ACTIVE_STATUSES = frozenset({"approved", "staged", "installed"})


@dataclass
class CompoundingMetrics:
    workspace_id: str
    total_mutations: int
    active_mutations: int
    promoted_mutations: int
    avg_quality_score: float
    total_tool_uses_by_generated: int
    mutation_age_days: float
    divergence_score: float
    tools_contributed: int
    prompts_evolved: int
    code_mutations_merged: int

    def to_dict(self) -> dict:
        return asdict(self)


def compute_compounding_metrics(workspace_id: str = "default") -> CompoundingMetrics:
    store = get_mutation_store()
    records, total = store.list_mutations(workspace_id, page=1, per_page=10_000)
    now = datetime.now(timezone.utc)

    active = [row for row in records if row.status in _ACTIVE_STATUSES]
    promoted = [row for row in records if row.metadata.get("promoted")]
    tool_records = [row for row in active if row.tier == "tool" and row.status == "approved"]
    prompt_keys = {row.name for row in records if row.tier == "prompt" and row.status in {"approved", "rolled_back"}}
    code_merged = sum(1 for row in records if row.tier == "code" and row.status == "approved")

    quality_scores = [row.quality_score for row in active if row.quality_score is not None]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
    total_uses = sum(row.use_count for row in records if row.tier == "tool")

    ages = []
    for row in active:
        anchor = row.approved_at or row.recorded_at
        ages.append((now - anchor).total_seconds() / 86400.0)
    mutation_age_days = sum(ages) / len(ages) if ages else 0.0

    tools_contributed = len(tool_records)
    prompts_evolved = len(prompt_keys)
    promoted_count = len(promoted)

    divergence_score = _compute_divergence_score(
        tools_contributed=tools_contributed,
        prompts_evolved=prompts_evolved,
        code_mutations_merged=code_merged,
        promoted_mutations=promoted_count,
    )

    return CompoundingMetrics(
        workspace_id=workspace_id,
        total_mutations=total,
        active_mutations=len(active),
        promoted_mutations=promoted_count,
        avg_quality_score=round(avg_quality, 4),
        total_tool_uses_by_generated=total_uses,
        mutation_age_days=round(mutation_age_days, 2),
        divergence_score=divergence_score,
        tools_contributed=tools_contributed,
        prompts_evolved=prompts_evolved,
        code_mutations_merged=code_merged,
    )


def _compute_divergence_score(
    *,
    tools_contributed: int,
    prompts_evolved: int,
    code_mutations_merged: int,
    promoted_mutations: int,
) -> float:
    if not any([tools_contributed, prompts_evolved, code_mutations_merged, promoted_mutations]):
        return 0.0
    tools_component = min(tools_contributed / 50.0, 1.0) * 0.35
    prompts_component = min(prompts_evolved / 10.0, 1.0) * 0.25
    code_component = min(code_mutations_merged / 10.0, 1.0) * 0.25
    promoted_component = min(promoted_mutations / 20.0, 1.0) * 0.15
    score = tools_component + prompts_component + code_component + promoted_component
    return round(min(max(score, 0.0), 1.0), 4)


def active_mutations_daily_series(workspace_id: str = "default") -> dict[str, list]:
    """Approximate active mutation count per day for the last 30 days."""
    store = get_mutation_store()
    records, _total = store.list_mutations(workspace_id, page=1, per_page=10_000)
    today = datetime.now(timezone.utc).date()
    buckets: dict[str, int] = {}
    for offset in range(29, -1, -1):
        day = today - timedelta(days=offset)
        count = _active_count_on_day(records, day)
        buckets[day.isoformat()] = count
    return {
        "labels": list(buckets.keys()),
        "values": list(buckets.values()),
    }


def _active_count_on_day(records: list[MutationRecord], day) -> int:
    count = 0
    for record in records:
        if record.status not in _ACTIVE_STATUSES:
            continue
        anchor = (record.approved_at or record.recorded_at).date()
        if anchor <= day:
            count += 1
    return count
