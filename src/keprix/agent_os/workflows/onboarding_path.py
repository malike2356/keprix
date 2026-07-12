"""Workflow 2: Onboarding Path Builder.

INPUT: product/service description
  → welcome sequence → first-call prep → walkthrough → day-1/7/30 checklist
OUTPUT: progressive onboarding experience package
"""

from __future__ import annotations

from typing import Any


def generate_onboarding_path(*, product: str, audience: str = "new users") -> dict[str, Any]:
    product = (product or "").strip() or "the product"
    audience = (audience or "new users").strip() or "new users"

    welcome = [
        {
            "step": 1,
            "title": "Welcome",
            "copy": f"Welcome. {product} helps {audience} get a first useful result without learning five tools.",
        },
        {
            "step": 2,
            "title": "One job",
            "copy": f"Today you have one job: run the Hello World / first workflow for {product}.",
        },
        {
            "step": 3,
            "title": "One folder",
            "copy": "Stay inside your workspace folder. Approval gates stay on for destructive actions.",
        },
    ]

    first_call = {
        "agenda": [
            f"Confirm the outcome {audience} care about with {product}",
            "Show the single vault / memory rule",
            "Run one workflow end to end",
            "Agree day-7 success metric",
        ],
        "prep_questions": [
            f"What does a win look like after 7 days with {product}?",
            "Which channel do you already use daily?",
            "What must never be automated without approval?",
        ],
    }

    walkthrough = [
        {"id": "install", "title": "Install / open Keprix", "detail": "Local install or hosted URL."},
        {"id": "provider", "title": "Connect one model provider", "detail": "`keprix model` or setup UI."},
        {"id": "hello", "title": "Run Hello World", "detail": "`keprix agent-os hello`."},
        {"id": "vault", "title": "Confirm the single vault", "detail": "Default `~/.keprix/vault` or custom folder."},
        {"id": "workflow", "title": "Run one Phase 2/4 workflow", "detail": "Content, CRM, SEO, or onboarding path."},
    ]

    checklist = {
        "day_1": [
            "Provider connected",
            "First chat or Hello World succeeds",
            "Vault configured (or auto-created)",
            "One workflow produces an artifact",
        ],
        "day_7": [
            "Memory notes appear in the vault",
            "At least 3 workflows used",
            "One channel connected (optional but recommended)",
            "Skill proposal reviewed or approved",
        ],
        "day_30": [
            "Agent OS glass used as daily pane",
            "Sub-agent / Kanban board in use",
            "Token budget reviewed",
            "One repeatable workflow promoted to automation",
        ],
    }

    steps = [
        {"id": "welcome", "title": "Welcome sequence", "status": "done"},
        {"id": "first-call", "title": "First-call prep", "status": "done"},
        {"id": "walkthrough", "title": "System walkthrough", "status": "done"},
        {"id": "checklist", "title": "Day 1/7/30 checklist", "status": "done"},
        {"id": "human-tune", "title": "Tune copy for brand voice", "status": "todo"},
    ]

    markdown = [
        f"# Onboarding path: {product}",
        "",
        f"Audience: {audience}",
        "",
        "## Welcome sequence",
    ]
    for item in welcome:
        markdown.extend(["", f"### {item['step']}. {item['title']}", item["copy"]])
    markdown.extend(["", "## First-call prep", "", "### Agenda"])
    for line in first_call["agenda"]:
        markdown.append(f"- {line}")
    markdown.extend(["", "### Prep questions"])
    for line in first_call["prep_questions"]:
        markdown.append(f"- {line}")
    markdown.extend(["", "## System walkthrough"])
    for item in walkthrough:
        markdown.append(f"- **{item['title']}**: {item['detail']}")
    for label, items in (("Day 1", checklist["day_1"]), ("Day 7", checklist["day_7"]), ("Day 30", checklist["day_30"])):
        markdown.extend(["", f"## {label} checklist"])
        for item in items:
            markdown.append(f"- [ ] {item}")

    return {
        "status": "ok",
        "workflow": "onboarding-path",
        "product": product,
        "audience": audience,
        "welcome": welcome,
        "first_call": first_call,
        "walkthrough": walkthrough,
        "checklist": checklist,
        "steps": steps,
        "output": "\n".join(markdown),
        "artifact": {
            "type": "onboarding_path",
            "product": product,
            "auto_skill": True,
        },
    }
