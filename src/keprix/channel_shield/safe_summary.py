"""Channel-aware safe summary generator (never includes live payloads)."""

from __future__ import annotations

from keprix.channel_shield.types import PipelineReport, ShieldEnvelope, Verdict

CHANNEL_LIMITS = {
    "email": 2000,
    "slack": 1500,
    "teams": 1500,
    "telegram": 3500,
    "whatsapp": 900,
    "discord": 1500,
    "sms": 280,
    "web": 1200,
}


def generate_safe_summary(
    envelope: ShieldEnvelope,
    report: PipelineReport,
    *,
    ui_deep_link: str | None = None,
) -> str:
    limit = CHANNEL_LIMITS.get(envelope.channel, 1200)
    verdict = report.verdict.value
    reasons = "; ".join(report.reasons[:4]) if report.reasons else "policy hold"
    subject = envelope.subject.strip() if envelope.subject else "(no subject)"
    sender = envelope.from_addr or "unknown sender"
    att_count = len(envelope.attachments)
    link_count = len(envelope.links)

    lines = [
        f"[Channel Shield] Message held ({verdict}).",
        f"Channel: {envelope.channel}",
        f"From: {sender}",
        f"Subject: {subject}",
        f"Attachments: {att_count}; links: {link_count}",
        f"Reasons: {reasons}",
        "Live content and files were not delivered.",
    ]
    if ui_deep_link:
        lines.append(f"Review: {ui_deep_link}")
    if report.verdict == Verdict.CLEAN:
        # Should not normally notify on clean; keep defensive
        lines = [
            f"[Channel Shield] Message delivered after scan ({verdict}).",
            f"From: {sender}",
            f"Subject: {subject}",
        ]
    text = "\n".join(lines)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."
