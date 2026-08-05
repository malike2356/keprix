"""Stable operational status bar model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StatusSnapshot:
    model: str = "none"
    provider: str = "none"
    transport: str = "http"
    session_id: str = ""
    queue_depth: int = 0
    busy_mode: str = "interrupt"
    token_count: int = 0
    latency_ms: int = 0
    cost_estimate: float = 0.0
    backend_healthy: bool = False
    agent_busy: bool = False
    voice_state: str = "off"


def short_session_id(session_id: str) -> str:
    cleaned = session_id.strip()
    if not cleaned:
        return "none"
    return cleaned[:8]


def format_tokens(count: int) -> str:
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(max(0, count))


def format_cost(value: float) -> str:
    if value <= 0:
        return "-"
    if value < 0.01:
        return f"${value:.4f}"
    return f"${value:.2f}"


def segment(label: str, value: str, *, width: int) -> str:
    raw = f"{label}:{value}"
    if len(raw) > width:
        return raw[: max(0, width - 1)] + "~"
    return raw.ljust(width)


def status_segments(snapshot: StatusSnapshot) -> list[tuple[str, str, int]]:
    health = "online" if snapshot.backend_healthy else "OFFLINE"
    busy = "busy" if snapshot.agent_busy else "idle"
    return [
        ("health", health, 14),
        ("agent", busy, 10),
        ("model", snapshot.model or "none", 18),
        ("provider", snapshot.provider or "none", 16),
        ("transport", snapshot.transport or "http", 16),
        ("session", short_session_id(snapshot.session_id), 16),
        ("queue", str(max(0, snapshot.queue_depth)), 9),
        ("mode", snapshot.busy_mode or "interrupt", 16),
        ("tokens", format_tokens(snapshot.token_count), 13),
        ("latency", f"{max(0, snapshot.latency_ms)}ms", 15),
        ("cost", format_cost(snapshot.cost_estimate), 13),
        ("voice", snapshot.voice_state or "off", 16),
    ]


def render_status_bar(snapshot: StatusSnapshot, *, width: int = 120) -> str:
    joined = " ".join(segment(label, value, width=seg_width) for label, value, seg_width in status_segments(snapshot))
    if len(joined) > width:
        return joined[: max(0, width - 1)] + "~"
    return joined.ljust(width)


__all__ = [
    "StatusSnapshot",
    "format_cost",
    "format_tokens",
    "render_status_bar",
    "short_session_id",
    "status_segments",
]
