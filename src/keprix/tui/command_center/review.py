"""Last-turn review report model."""

from __future__ import annotations

from dataclasses import dataclass, field

from keprix.tui.runtime_store import RuntimeStore


@dataclass(frozen=True)
class ReviewReport:
    user_request_summary: str = "None recorded"
    assistant_outcome_summary: str = "None recorded"
    files_changed: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    subagents_used: list[str] = field(default_factory=list)
    commands_executed: list[str] = field(default_factory=list)
    risks_or_warnings: list[str] = field(default_factory=list)
    tests_run: list[str] = field(default_factory=list)
    pending_next_actions: list[str] = field(default_factory=list)
    token_usage: int = 0
    latency_ms: int = 0
    cost_estimate: float = 0.0


def _compact(text: str, *, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return "None recorded"
    if len(cleaned) > limit:
        return cleaned[: limit - 1] + "~"
    return cleaned


def _list_or_none(values: list[str]) -> list[str]:
    return [value for value in values if value.strip()] or ["None recorded"]


def build_review_report(
    store: RuntimeStore,
    *,
    user_request: str = "",
    assistant_outcome: str = "",
) -> ReviewReport:
    return ReviewReport(
        user_request_summary=_compact(user_request),
        assistant_outcome_summary=_compact(assistant_outcome),
        files_changed=list(store.files_changed),
        tools_used=[f"{tool.name} ({tool.status})" for tool in store.tools],
        subagents_used=[f"{item.label} ({item.status})" for item in store.subagents.values()],
        commands_executed=list(store.commands_executed),
        risks_or_warnings=list(store.risks_or_warnings),
        tests_run=list(store.tests_run),
        pending_next_actions=list(store.pending_next_actions),
        token_usage=store.turn.total_tokens,
        latency_ms=store.turn.latency_ms,
        cost_estimate=store.turn.cost_estimate,
    )


def render_review_report(report: ReviewReport) -> str:
    lines = [
        "Last turn review",
        "",
        "User request",
        report.user_request_summary,
        "",
        "Assistant outcome",
        report.assistant_outcome_summary,
        "",
        "Files changed",
    ]
    sections = [
        _list_or_none(report.files_changed),
        ["", "Tools used", *_list_or_none(report.tools_used)],
        ["", "Subagents used", *_list_or_none(report.subagents_used)],
        ["", "Commands executed", *_list_or_none(report.commands_executed)],
        ["", "Risks or warnings", *_list_or_none(report.risks_or_warnings)],
        ["", "Tests run", *_list_or_none(report.tests_run)],
        ["", "Pending next actions", *_list_or_none(report.pending_next_actions)],
        [
            "",
            "Usage",
            f"Tokens: {report.token_usage}",
            f"Latency: {report.latency_ms} ms",
            f"Cost: {report.cost_estimate:.4f}" if report.cost_estimate else "Cost: None recorded",
        ],
    ]
    for section in sections:
        for index, value in enumerate(section):
            if value == "":
                lines.append("")
            elif index == 0 and section is sections[0]:
                lines.append(f"- {value}")
            elif value in {
                "Tools used",
                "Subagents used",
                "Commands executed",
                "Risks or warnings",
                "Tests run",
                "Pending next actions",
                "Usage",
            }:
                lines.append(value)
            elif value.startswith(("Tokens:", "Latency:", "Cost:")):
                lines.append(value)
            else:
                lines.append(f"- {value}")
    return "\n".join(lines)


__all__ = ["ReviewReport", "build_review_report", "render_review_report"]
