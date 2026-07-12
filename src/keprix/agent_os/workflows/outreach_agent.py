"""Workflow 6: Outreach / Lead Agent.

INPUT: audience + offer
  → content calendar → hooks → follow-up sequence → next steps per lead stage
OUTPUT: lead generation + nurturing system package
"""

from __future__ import annotations

from typing import Any


def generate_outreach_package(
    *,
    audience: str,
    offer: str,
    channels: list[str] | None = None,
    days: int = 14,
) -> dict[str, Any]:
    audience = (audience or "").strip() or "target buyers"
    offer = (offer or "").strip() or "a free working demo"
    selected = channels or ["linkedin", "email", "x"]
    selected = [c.strip().lower() for c in selected if c and c.strip()]
    horizon = max(7, min(int(days or 14), 60))

    calendar = []
    themes = [
        "problem awareness",
        "proof / case",
        "offer clarity",
        "objection handling",
        "soft CTA",
    ]
    for day in range(1, horizon + 1):
        theme = themes[(day - 1) % len(themes)]
        channel = selected[(day - 1) % len(selected)]
        calendar.append(
            {
                "day": day,
                "channel": channel,
                "theme": theme,
                "post": f"Day {day} for {audience}: talk about {theme} and point to {offer}.",
            }
        )

    hooks = [
        f"{audience.title()} are busy. {offer} should remove one painful step this week.",
        f"If {audience} still stitch five tools together, the system is the bottleneck.",
        f"One workflow. One vault. One offer: {offer}.",
    ]

    followups = [
        {
            "day": 0,
            "channel": "email",
            "subject": f"Quick idea for {audience}",
            "body": f"Saw you working on this space. Would {offer} be useful this week?",
        },
        {
            "day": 3,
            "channel": "email",
            "subject": "Sharing the checklist",
            "body": f"Sending the short checklist we use before pitching {offer}. Happy to walk through it.",
        },
        {
            "day": 7,
            "channel": "linkedin",
            "subject": "Bump",
            "body": f"Circling back once. If timing is off, who on your team owns evaluations for {offer}?",
        },
    ]

    lead_map = [
        {"stage": "new", "next_step": "Qualify pain + fit in one reply", "owner": "outreach-agent"},
        {"stage": "engaged", "next_step": "Send proof asset + book a 15-min call", "owner": "outreach-agent"},
        {"stage": "qualified", "next_step": "Hand off to human with notes + CRM fields", "owner": "human"},
        {"stage": "closed_lost", "next_step": "Park in 30-day nurture calendar", "owner": "outreach-agent"},
    ]

    steps = [
        {"id": "calendar", "title": "Build content calendar", "status": "done"},
        {"id": "hooks", "title": "Write platform hooks", "status": "done"},
        {"id": "sequence", "title": "Sequence follow-ups", "status": "done"},
        {"id": "lead-map", "title": "Map next steps per lead stage", "status": "done"},
        {"id": "approve", "title": "Human approve outbound copy", "status": "todo"},
    ]

    markdown = [
        f"# Outreach package for {audience}",
        "",
        f"Offer: {offer}",
        f"Channels: {', '.join(selected)}",
        f"Horizon: {horizon} days",
        "",
        "## Hooks",
        *[f"- {hook}" for hook in hooks],
        "",
        "## Calendar (first 7 days)",
    ]
    for row in calendar[:7]:
        markdown.append(f"- Day {row['day']} · {row['channel']}: {row['post']}")
    markdown.extend(["", "## Follow-up sequence"])
    for item in followups:
        markdown.extend(
            [
                "",
                f"### Day {item['day']} · {item['channel']}",
                f"Subject: {item['subject']}",
                item["body"],
            ]
        )
    markdown.extend(["", "## Lead stage map"])
    for row in lead_map:
        markdown.append(f"- **{row['stage']}**: {row['next_step']} ({row['owner']})")

    return {
        "status": "ok",
        "workflow": "outreach-agent",
        "audience": audience,
        "offer": offer,
        "channels": selected,
        "days": horizon,
        "calendar": calendar,
        "hooks": hooks,
        "followups": followups,
        "lead_map": lead_map,
        "steps": steps,
        "output": "\n".join(markdown),
        "artifact": {
            "type": "outreach_package",
            "audience": audience,
            "calendar_days": horizon,
            "auto_skill": True,
        },
    }
