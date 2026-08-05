"""Aggregate operator dashboard context for the Keprix copilot."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

_INTERRUPTED_STATUSES = frozenset(
    {"interrupted", "waiting_for_approval", "paused"},
)


@dataclass
class OperatorContextBundle:
    staged_mutations: int
    interrupted_playbooks: int
    channel_issues: list[dict[str, str]] = field(default_factory=list)
    recent_failed_runs: list[dict[str, str]] = field(default_factory=list)
    summary_markdown: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def build_operator_context(
    workspace_id: str = "default",
    *,
    detail: str = "nav",
) -> OperatorContextBundle:
    """Build a redacted operator snapshot (no secrets).

    ``detail`` is reserved for nav vs full payloads; both currently return the same bundle.
    """
    _ = detail
    staged = _staged_mutation_count(workspace_id)
    interrupted_runs = _interrupted_playbook_runs(workspace_id)
    channel_issues = await _channel_issues()
    failed_runs = _recent_failed_playbook_runs(workspace_id, limit=3)

    lines = [
        "## Keprix operator snapshot",
        "",
        f"- **Staged mutations:** {staged}",
        f"- **Interrupted playbooks:** {len(interrupted_runs)}",
        f"- **Channel issues:** {len(channel_issues)}",
        f"- **Recent failed playbook runs:** {len(failed_runs)}",
        "",
    ]
    if staged:
        lines.append("Review staged mutations at `/admin/mutations?status=staged`.")
    if interrupted_runs:
        lines.append("Resume or inspect interrupted runs at `/playbooks`.")
    if channel_issues:
        names = ", ".join(item.get("name", "?") for item in channel_issues[:5])
        lines.append(f"Unhealthy channels: {names}. Open `/admin/channels` or Settings → Messaging.")
    if failed_runs:
        last = failed_runs[0]
        lines.append(
            f"Latest failure: run `{last.get('run_id', '?')}` on graph `{last.get('graph_id', '?')}`. "
            f"Error: {last.get('error', 'unknown')}"
        )

    return OperatorContextBundle(
        staged_mutations=staged,
        interrupted_playbooks=len(interrupted_runs),
        channel_issues=channel_issues,
        recent_failed_runs=failed_runs,
        summary_markdown="\n".join(lines).strip(),
    )


def _staged_mutation_count(workspace_id: str) -> int:
    try:
        from keprix.mutation.store import get_mutation_store

        raw = get_mutation_store().mutation_stats(workspace_id)
        counts = raw.get("counts") or {}
        return sum(tier_counts.get("staged", 0) for tier_counts in counts.values())
    except Exception:
        return 0


# Alias used by operator copilot tools.
_staged_mutation_count_sync = _staged_mutation_count


def _interrupted_playbook_runs(workspace_id: str) -> list[dict[str, str]]:
    try:
        from keprix.playbook.runtime import playbook_registry

        runs = playbook_registry.list_runs(workspace_id=workspace_id, limit=200)
        rows: list[dict[str, str]] = []
        for run in runs:
            if run.status.value not in _INTERRUPTED_STATUSES:
                continue
            rows.append(
                {
                    "run_id": run.run_id,
                    "graph_id": run.graph_id,
                    "status": run.status.value,
                    "current_node": run.current_node or "",
                }
            )
        return rows
    except Exception:
        return []


async def _channel_issues() -> list[dict[str, str]]:
    try:
        from keprix.config.health_monitor import ConfigHealthMonitor

        monitor = ConfigHealthMonitor()
        await monitor._run_all_checks()
        issues: list[dict[str, str]] = []
        for name, health in monitor.get_all().items():
            if not name.startswith("channel:"):
                continue
            if health.status == "healthy":
                continue
            channel_name = name.removeprefix("channel:")
            severity = "degraded" if health.status == "warning" else "error"
            issues.append(
                {
                    "id": channel_name,
                    "name": channel_name.replace("_", " ").title(),
                    "status": severity,
                    "detail": (health.error or health.message or health.status)[:240],
                }
            )
        return issues
    except Exception:
        return []


def _recent_failed_playbook_runs(workspace_id: str, *, limit: int = 3) -> list[dict[str, str]]:
    try:
        from keprix.playbook.runtime import playbook_registry

        runs = playbook_registry.list_runs(workspace_id=workspace_id, limit=200)
        failed: list[dict[str, str]] = []
        for run in runs:
            if run.status.value != "failed":
                continue
            failed.append(
                {
                    "run_id": run.run_id,
                    "graph_id": run.graph_id,
                    "status": run.status.value,
                    "error": (run.error or "unknown error")[:240],
                    "current_node": run.current_node or "",
                }
            )
            if len(failed) >= limit:
                break
        return failed
    except Exception:
        return []
