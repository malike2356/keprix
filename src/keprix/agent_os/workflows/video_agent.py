"""Workflow 3: Video Agent.

INPUT: topic
  → script → storyboard → production checklist → description/tags/thumbnail
OUTPUT: video package ready for human review / publish
"""

from __future__ import annotations

from typing import Any


def generate_video_package(*, topic: str, audience: str = "general", length_minutes: int = 8) -> dict[str, Any]:
    topic = (topic or "").strip() or "Untitled video"
    audience = (audience or "general").strip() or "general"
    minutes = max(3, min(int(length_minutes or 8), 30))

    hook = f"Most people get {topic} wrong in the first 30 seconds."
    acts = [
        {
            "act": 1,
            "title": "Hook + promise",
            "seconds": 20,
            "narration": f"{hook} In the next {minutes} minutes you will leave with a clear plan for {topic}.",
            "visual": "Bold title card, then talking head or screen open.",
        },
        {
            "act": 2,
            "title": "Problem",
            "seconds": max(40, minutes * 8),
            "narration": f"For {audience}, the usual approach to {topic} creates friction and wasted tokens/time.",
            "visual": "Simple diagram of the broken workflow.",
        },
        {
            "act": 3,
            "title": "Method",
            "seconds": max(60, minutes * 25),
            "narration": f"Here is a three-step method for {topic}: clarify the outcome, run one agent workflow, review the artifact.",
            "visual": "Step cards 1-2-3 with screen recordings placeholders.",
        },
        {
            "act": 4,
            "title": "Proof + CTA",
            "seconds": max(30, minutes * 10),
            "narration": f"Ship the first {topic} draft today. Comment with your niche and I will reply with the next step.",
            "visual": "Before/after artifact, end screen with subscribe + link.",
        },
    ]

    storyboard = [
        {"shot": idx, "visual": act["visual"], "narration": act["narration"], "act": act["title"]}
        for idx, act in enumerate(acts, start=1)
    ]
    description = (
        f"{topic} for {audience}.\n\n"
        f"In this video: the common mistake, a {minutes}-minute method, and a publish-ready checklist.\n\n"
        "Chapters:\n"
        + "\n".join(f"0:{act['seconds'] // 60:02d} {act['title']}" for act in acts)
        + "\n\n#keprix #agentos"
    )
    tags = [topic.lower().replace(" ", "-"), "agent-os", "tutorial", audience.lower().replace(" ", "-"), "howto"]
    thumbnail_text = [f"{topic}", "Stop guessing", "Watch this"]

    production = [
        {"id": "script", "title": "Lock narration script", "status": "done"},
        {"id": "storyboard", "title": "Approve storyboard shots", "status": "done"},
        {"id": "record", "title": "Record / gather B-roll (human)", "status": "todo"},
        {"id": "edit", "title": "Edit + captions (human or editor)", "status": "todo"},
        {"id": "publish", "title": "Publish with description + tags", "status": "todo"},
    ]

    markdown = [
        f"# Video package: {topic}",
        "",
        f"Audience: {audience} · Target length: ~{minutes} minutes",
        "",
        "## Script",
    ]
    for act in acts:
        markdown.extend(["", f"### Act {act['act']}: {act['title']}", "", act["narration"]])
    markdown.extend(["", "## Storyboard"])
    for shot in storyboard:
        markdown.append(f"- Shot {shot['shot']}: {shot['visual']}")
    markdown.extend(
        [
            "",
            "## Description",
            "",
            "```",
            description,
            "```",
            "",
            "## Tags",
            ", ".join(tags),
            "",
            "## Thumbnail text options",
            *[f"- {line}" for line in thumbnail_text],
        ]
    )

    return {
        "status": "ok",
        "workflow": "video-agent",
        "topic": topic,
        "audience": audience,
        "length_minutes": minutes,
        "script": acts,
        "storyboard": storyboard,
        "description": description,
        "tags": tags,
        "thumbnail_text": thumbnail_text,
        "steps": production,
        "output": "\n".join(markdown),
        "artifact": {
            "type": "video_package",
            "topic": topic,
            "shot_count": len(storyboard),
            "auto_skill": True,
        },
    }
