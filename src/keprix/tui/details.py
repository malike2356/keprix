"""Details panel sections: thinking, tools, subagents, activity (Prompt 206)."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Literal

Section = Literal["thinking", "tools", "subagents", "activity"]
SectionMode = Literal["hidden", "collapsed", "expanded"]

SECTION_ORDER: tuple[Section, ...] = ("thinking", "tools", "subagents", "activity")
MODE_CYCLE: tuple[SectionMode, ...] = ("hidden", "collapsed", "expanded")

DEFAULT_DETAILS_MODES: dict[Section, SectionMode] = {
    "thinking": "collapsed",
    "tools": "collapsed",
    "subagents": "collapsed",
    "activity": "hidden",
}


def cycle_mode(current: str) -> SectionMode:
    """Advance hidden -> collapsed -> expanded -> hidden."""
    normalized = current.strip().lower()
    if normalized not in MODE_CYCLE:
        return "collapsed"
    idx = MODE_CYCLE.index(normalized)  # type: ignore[arg-type]
    return MODE_CYCLE[(idx + 1) % len(MODE_CYCLE)]


def parse_section_mode(value: str) -> SectionMode | None:
    normalized = value.strip().lower()
    if normalized in MODE_CYCLE:
        return normalized  # type: ignore[return-value]
    return None


def parse_section_name(value: str) -> Section | None:
    normalized = value.strip().lower()
    if normalized == "all":
        return None
    if normalized in SECTION_ORDER:
        return normalized  # type: ignore[return-value]
    return None


@dataclass
class DetailsConfig:
    modes: dict[Section, SectionMode] = field(default_factory=lambda: dict(DEFAULT_DETAILS_MODES))

    @classmethod
    def from_mapping(cls, raw: dict[str, str] | None) -> DetailsConfig:
        modes = dict(DEFAULT_DETAILS_MODES)
        if isinstance(raw, dict):
            for key, value in raw.items():
                section = parse_section_name(str(key))
                mode = parse_section_mode(str(value))
                if section is not None and mode is not None:
                    modes[section] = mode
        return cls(modes=modes)

    def set_mode(self, section: Section, mode: SectionMode) -> None:
        self.modes[section] = mode

    def set_all(self, mode: SectionMode) -> None:
        for section in SECTION_ORDER:
            self.modes[section] = mode

    def format_status(self) -> str:
        lines = ["Details section modes:"]
        for section in SECTION_ORDER:
            lines.append(f"  {section}: {self.modes[section]}")
        lines.append("Usage: /details [section mode] | /details all collapsed")
        return "\n".join(lines)


@dataclass
class ToolStep:
    name: str
    status: str = "running"
    started_at: float = field(default_factory=time.monotonic)
    finished_at: float | None = None

    @property
    def duration_sec(self) -> float | None:
        if self.finished_at is None:
            if self.status == "running":
                return time.monotonic() - self.started_at
            return None
        return max(0.0, self.finished_at - self.started_at)


@dataclass
class ToolTrail:
    steps: list[ToolStep] = field(default_factory=list)
    thinking_lines: list[str] = field(default_factory=list)

    def start_tool(self, name: str) -> None:
        self.steps.append(ToolStep(name=name or "tool", status="running"))

    def finish_tool(self, name: str, status: str = "done") -> None:
        target = name or "tool"
        for step in reversed(self.steps):
            if step.name == target and step.status == "running":
                step.status = status
                step.finished_at = time.monotonic()
                return
        self.steps.append(
            ToolStep(
                name=target,
                status=status,
                started_at=time.monotonic(),
                finished_at=time.monotonic(),
            )
        )

    def add_thinking(self, line: str) -> None:
        text = line.strip()
        if text:
            self.thinking_lines.append(text)

    def running_count(self) -> int:
        return sum(1 for step in self.steps if step.status == "running")

    def done_count(self) -> int:
        return sum(1 for step in self.steps if step.status != "running")

    def render_tools(self, mode: SectionMode) -> list[str]:
        if mode == "hidden" or not self.steps:
            return []
        running = self.running_count()
        done = self.done_count()
        if mode == "collapsed":
            return [f"[tools] {running} running, {done} done"]
        lines = [f"[tools] {running} running, {done} done"]
        for step in self.steps:
            status_label = "run" if step.status == "running" else step.status
            duration = step.duration_sec
            suffix = f" ({int(duration)}s)" if duration is not None and duration >= 1 else ""
            lines.append(f"  {status_label:<7} {step.name}{suffix}")
        return lines

    def render_thinking(self, mode: SectionMode) -> list[str]:
        if mode == "hidden" or not self.thinking_lines:
            return []
        if mode == "collapsed":
            preview = self.thinking_lines[-1]
            short = preview[:72] + "..." if len(preview) > 72 else preview
            return [f"[thinking] {short}"]
        lines = ["[thinking]"]
        lines.extend(f"  {line}" for line in self.thinking_lines[-12:])
        return lines


@dataclass
class SubagentRecord:
    subagent_id: str
    label: str
    status: str = "running"
    started_at: float = field(default_factory=time.monotonic)
    finished_at: float | None = None
    cost_hint: str = ""

    @property
    def duration_sec(self) -> float | None:
        end = self.finished_at or (time.monotonic() if self.status == "running" else None)
        if end is None:
            return None
        return max(0.0, end - self.started_at)


@dataclass
class SubagentList:
    records: dict[str, SubagentRecord] = field(default_factory=dict)

    def spawn(self, subagent_id: str, *, label: str = "") -> None:
        sid = subagent_id or f"subagent-{len(self.records) + 1}"
        self.records[sid] = SubagentRecord(subagent_id=sid, label=label or sid)

    def complete(self, subagent_id: str, *, label: str = "", cost_hint: str = "") -> None:
        sid = subagent_id or ""
        record = self.records.get(sid)
        if record is None:
            record = SubagentRecord(subagent_id=sid or label or "subagent", label=label or sid)
            self.records[record.subagent_id] = record
        record.status = "done"
        record.finished_at = time.monotonic()
        if label:
            record.label = label
        if cost_hint:
            record.cost_hint = cost_hint

    def render(self, mode: SectionMode) -> list[str]:
        if mode == "hidden" or not self.records:
            return []
        items = list(self.records.values())
        running = sum(1 for item in items if item.status == "running")
        done = len(items) - running
        if mode == "collapsed":
            return [f"[subagents] {running} running, {done} done"]
        lines = ["[subagents]"]
        for item in items:
            duration = item.duration_sec
            extra = ""
            if item.status == "done" and (item.cost_hint or duration is not None):
                parts: list[str] = []
                if item.cost_hint:
                    parts.append(item.cost_hint)
                if duration is not None:
                    parts.append(f"{int(duration)}s")
                extra = f" (+{', '.join(parts)})" if parts else ""
            lines.append(f"  {item.label[:40]:<40} {item.status:<7}{extra}")
        return lines


class ActivityFeed:
    """Transient status lines (max 8), cleared on turn end."""

    def __init__(self, *, max_lines: int = 8) -> None:
        self._max_lines = max_lines
        self._lines: deque[str] = deque(maxlen=max_lines)

    def push(self, line: str) -> None:
        text = line.strip()
        if text:
            self._lines.append(text)

    def clear(self) -> None:
        self._lines.clear()

    def render(self, mode: SectionMode) -> list[str]:
        if mode == "hidden" or not self._lines:
            return []
        if mode == "collapsed":
            return [f"[activity] {self._lines[-1]}"]
        lines = ["[activity]"]
        lines.extend(f"  {line}" for line in self._lines)
        return lines


def render_details_panel(
    *,
    config: DetailsConfig,
    trail: ToolTrail,
    subagents: SubagentList,
    activity: ActivityFeed,
) -> str:
    sections: list[str] = []
    sections.extend(trail.render_thinking(config.modes["thinking"]))
    sections.extend(trail.render_tools(config.modes["tools"]))
    sections.extend(subagents.render(config.modes["subagents"]))
    sections.extend(activity.render(config.modes["activity"]))
    return "\n".join(sections)
