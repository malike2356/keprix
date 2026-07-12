"""Workflow 1: Content Series Generator.

INPUT: topic + audience questions
  → hooks → scripts → captions → cross-platform variants
OUTPUT: publish-ready content series (sub-steps can land on Kanban)
"""

from __future__ import annotations

from typing import Any


_PLATFORM_HINTS = {
    "linkedin": "Professional tone, 1-3 short paragraphs, soft CTA.",
    "x": "Punchy under 260 chars, one clear claim.",
    "youtube": "Hook in first 8 seconds, chapters, end screen CTA.",
    "instagram": "Visual-first caption, 3-5 hashtags, save-worthy tip.",
    "email": "Subject + preview + body with one ask.",
}


def _parse_questions(raw: str) -> list[str]:
    parts = [line.strip(" -*\t") for line in (raw or "").splitlines() if line.strip()]
    if not parts and raw.strip():
        parts = [q.strip() for q in raw.split("?") if q.strip()]
        parts = [f"{q}?" if not q.endswith("?") else q for q in parts]
    return parts or ["What is the core problem this solves?", "What should they do next?"]


def generate_content_series(
    *,
    topic: str,
    audience_questions: str = "",
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    topic = (topic or "").strip() or "Untitled topic"
    questions = _parse_questions(audience_questions)
    selected = platforms or ["linkedin", "x", "youtube", "instagram", "email"]
    selected = [p.strip().lower() for p in selected if p and p.strip()]

    hooks = [
        f"Stop guessing on {topic}: here is the playbook.",
        f"The {topic} mistake almost everyone makes (and how to fix it).",
        f"One prompt → a full {topic} series your team can ship today.",
    ]
    scripts = []
    for idx, question in enumerate(questions, start=1):
        scripts.append(
            {
                "id": f"script-{idx}",
                "question": question,
                "script": (
                    f"Hook: {hooks[(idx - 1) % len(hooks)]}\n"
                    f"Body: Answer '{question}' with a concrete example about {topic}.\n"
                    f"Close: Tell the audience the next smallest action on {topic}."
                ),
            }
        )
    captions = [
        f"{topic}: start with the question your audience already asks. Answer it once, then reuse everywhere.",
        f"Series for {topic}: hook → proof → next step. Keep each piece under one idea.",
    ]
    variants = []
    for platform in selected:
        hint = _PLATFORM_HINTS.get(platform, "Keep it clear, one idea, one CTA.")
        variants.append(
            {
                "platform": platform,
                "guidance": hint,
                "draft": (
                    f"[{platform.upper()}] {topic}\n"
                    f"{hooks[0]}\n"
                    f"Answer: {questions[0]}\n"
                    f"CTA: Reply or click through for the full {topic} series."
                ),
            }
        )

    markdown_parts = [
        f"# Content series: {topic}",
        "",
        "## Hooks",
        *[f"- {hook}" for hook in hooks],
        "",
        "## Scripts",
    ]
    for item in scripts:
        markdown_parts.extend(["", f"### {item['question']}", "", "```", item["script"], "```"])
    markdown_parts.extend(["", "## Captions", *[f"- {cap}" for cap in captions], "", "## Cross-platform variants"])
    for variant in variants:
        markdown_parts.extend(["", f"### {variant['platform']}", "", "```", variant["draft"], "```"])

    steps = [
        {"id": "hooks", "title": f"Draft hooks for {topic}", "status": "done"},
        {"id": "scripts", "title": f"Write scripts ({len(scripts)} pieces)", "status": "done"},
        {"id": "captions", "title": "Generate captions", "status": "done"},
        {"id": "variants", "title": "Map cross-platform variants", "status": "done"},
        {"id": "review", "title": "Human review before publish", "status": "todo"},
    ]

    return {
        "status": "ok",
        "workflow": "content-series",
        "topic": topic,
        "hooks": hooks,
        "scripts": scripts,
        "captions": captions,
        "variants": variants,
        "steps": steps,
        "output": "\n".join(markdown_parts),
        "artifact": {
            "type": "content_series",
            "topic": topic,
            "piece_count": len(scripts),
            "platforms": selected,
        },
    }
