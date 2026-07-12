"""Token minimization playbook (Prompt 270 Task 5.1).

Ten techniques mapped onto existing Keprix compression, budget, and routing code.
"""

from __future__ import annotations

from typing import Any


TECHNIQUES: tuple[dict[str, Any], ...] = (
    {
        "id": "context_compress",
        "title": "Compress long sessions",
        "summary": "Summarize older turns before the context window fills.",
        "code": "agent/context_compressor.py",
        "default_on": True,
    },
    {
        "id": "budget_layer",
        "title": "Respect token budgets",
        "summary": "Warn and stop before overage using the budget layer.",
        "code": "agent/layers/budget.py",
        "default_on": True,
    },
    {
        "id": "skill_first",
        "title": "Prefer skills over raw prompting",
        "summary": "Load a short skill instead of restating long procedures each turn.",
        "code": "agent/skill_first.py",
        "default_on": True,
    },
    {
        "id": "model_tiering",
        "title": "Use the lightest capable model",
        "summary": "Route routine work to Luna/Terra-class models; reserve heavy models for hard jobs.",
        "code": "keprix model / providers",
        "default_on": True,
    },
    {
        "id": "tool_output_trim",
        "title": "Trim tool output",
        "summary": "Cap and summarize large tool results before feeding them back to the model.",
        "code": "providers/compression/",
        "default_on": True,
    },
    {
        "id": "one_vault",
        "title": "One vault, one memory",
        "summary": "Avoid multi-vault hunting that burns tokens searching for missing context.",
        "code": "vault/capture.py",
        "default_on": True,
    },
    {
        "id": "dedupe_prompts",
        "title": "Dedupe repeated system prompts",
        "summary": "Reuse cached instruction blocks and avoid re-pasting the same docs every turn.",
        "code": "agent/prompt_builder.py",
        "default_on": True,
    },
    {
        "id": "rtk_balanced",
        "title": "RTK / Caveman compression (optional)",
        "summary": "Enable provider compression pipeline for high-volume chats when quality allows.",
        "code": "providers/compression/compressor.py",
        "default_on": False,
    },
    {
        "id": "usage_glass",
        "title": "Watch per-agent spend",
        "summary": "Use /usage and Agent OS glass to catch wasteful agents early.",
        "code": "usage/ + agent_os/glass_dashboard.py",
        "default_on": True,
    },
    {
        "id": "plan_before_keys",
        "title": "Plan before raw API burn",
        "summary": "Prefer coding plans and scoped jobs so agents do not stop mid-task after burning tokens.",
        "code": "agent_os workflows + approvals",
        "default_on": True,
    },
)


def list_techniques() -> list[dict[str, Any]]:
    return [dict(item) for item in TECHNIQUES]


def playbook_markdown() -> str:
    lines = [
        "# Token Minimization Playbook",
        "",
        "Fewer tokens with the same outcomes. Keprix embeds these ten techniques:",
        "",
    ]
    for idx, item in enumerate(TECHNIQUES, start=1):
        flag = "on by default" if item["default_on"] else "opt-in"
        lines.extend(
            [
                f"## {idx}. {item['title']} ({flag})",
                "",
                item["summary"],
                f"Code: `{item['code']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## How to apply",
            "",
            "1. Keep context compression and budgets enabled.",
            "2. Switch models with `keprix model` instead of over-prompting.",
            "3. Review `/usage` By agent weekly.",
            "4. Turn on RTK compression only for high-volume channels.",
            "",
        ]
    )
    return "\n".join(lines)


def playbook_status() -> dict[str, Any]:
    return {
        "ok": True,
        "technique_count": len(TECHNIQUES),
        "techniques": list_techniques(),
        "markdown": playbook_markdown(),
        "links": {
            "usage": "/usage",
            "glass": "/agent-os/glass",
            "settings": "/dashboard/settings",
        },
    }
