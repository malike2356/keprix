"""Lean Aiva system prompt builder (product sidecar sessions)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

DEFAULT_TONE = "Professional, warm, concise. No jargon. Get to the point."
DEFAULT_AIVA_NAME = "Aiva"
DEFAULT_USER_NAME = "the user"
MAX_LEAN_CHARS = 12_000  # ~3K tokens at ~4 chars/token
_ENGINEERING_MARKERS = (
    "verlox monorepo",
    "build prompt",
    "scout architecture",
    "tui parity",
    "keprix codebase",
    "prompt implementation audit",
    "fowler",
)


def _prompts_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "prompts"


def _load_template(domain: str) -> str:
    name = {
        "property": "aiva_property.txt",
        "propreneur": "aiva_property.txt",
        "business": "aiva_business.txt",
    }.get((domain or "").strip().lower(), "aiva_default.txt")
    path = _prompts_dir() / name
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return _fallback_template()


def _fallback_template() -> str:
    return (
        "You are {aiva_name}, an AI assistant for {user_name}.\n\n"
        "## Your Tools\n{tool_list}\n\n"
        "## Tone\n{tone}\n\n"
        "## Rules\n- Never invent information.\n"
        "- Never send email or calendar invites without user approval.\n"
        "- Keep responses short.\n\n"
        "## Current Context\n{memory_injection}\n{calendar_today}\n"
        "{recent_emails_summary}\n{domain_knowledge}\n"
    )


def _format_tools(tools: list[Any] | None) -> str:
    names: list[str] = []
    for item in tools or []:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
            continue
        if isinstance(item, Mapping):
            name = str(item.get("name") or "").strip()
            if name:
                names.append(name)
    if not names:
        return "- (tools provided by the host product at runtime)"
    # Keep lean: names only, capped.
    uniq = []
    seen: set[str] = set()
    for name in names:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f"- {name}")
        if len(uniq) >= 40:
            uniq.append("- ...")
            break
    return "\n".join(uniq)


def _clean_block(label: str, value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    # Drop obviously engineering dumps if a caller smuggles them in.
    lowered = text.lower()
    if any(marker in lowered for marker in _ENGINEERING_MARKERS):
        return ""
    if len(text) > 1500:
        text = text[:1500].rstrip() + "..."
    return f"{label}: {text}"


def estimate_tokens(text: str) -> int:
    """Rough token estimate for lean-prompt budgets (chars/4)."""
    return max(1, (len(text) + 3) // 4) if text else 0


def build_aiva_system_prompt(
    *,
    aiva_name: str | None = None,
    user_name: str | None = None,
    tone: str | None = None,
    domain: str | None = None,
    tools: list[Any] | None = None,
    memory_injection: str | None = None,
    calendar_today: str | None = None,
    recent_emails_summary: str | None = None,
    domain_knowledge: str | None = None,
    workspace_overrides: Mapping[str, Any] | None = None,
) -> str:
    """Build a lean Aiva system prompt (target under ~3K tokens)."""
    overrides = dict(workspace_overrides or {})
    domain_key = str(overrides.get("domain") or domain or os.getenv("AIVA_PROMPT_DOMAIN") or "default")
    template = _load_template(domain_key)
    filled = template.format(
        aiva_name=str(overrides.get("aiva_name") or aiva_name or os.getenv("AIVA_NAME") or DEFAULT_AIVA_NAME),
        user_name=str(overrides.get("user_name") or user_name or os.getenv("AIVA_USER_NAME") or DEFAULT_USER_NAME),
        tool_list=_format_tools(overrides.get("tools") if "tools" in overrides else tools),
        tone=str(overrides.get("tone") or tone or os.getenv("AIVA_TONE") or DEFAULT_TONE),
        memory_injection=_clean_block("Memory", overrides.get("memory_injection", memory_injection)),
        calendar_today=_clean_block("Today calendar", overrides.get("calendar_today", calendar_today)),
        recent_emails_summary=_clean_block(
            "Recent emails", overrides.get("recent_emails_summary", recent_emails_summary)
        ),
        domain_knowledge=_clean_block(
            "Domain knowledge", overrides.get("domain_knowledge", domain_knowledge)
        ),
    )
    # Collapse excess blank lines for stable DeepSeek prefix caching.
    lines = [line.rstrip() for line in filled.splitlines()]
    compact: list[str] = []
    blank = 0
    for line in lines:
        if not line.strip():
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        compact.append(line)
    prompt = "\n".join(compact).strip() + "\n"
    if len(prompt) > MAX_LEAN_CHARS:
        prompt = prompt[:MAX_LEAN_CHARS].rstrip() + "\n"
    return prompt


def should_use_lean_aiva_prompt(product: str | None) -> bool:
    return str(product or "").strip().lower() == "aiva"
