"""Prompt templates for Aiva session compaction summaries."""

from __future__ import annotations

COMPACTION_SYSTEM = (
    "You compress chat history into a short factual summary for an AI assistant. "
    "Keep decisions, open tasks, names, dates, and commitments. "
    "Omit chit-chat and tool noise. Write plain prose, no markdown headings. "
    "Stay under 400 words."
)

COMPACTION_USER_TEMPLATE = """Previous summary (may be empty):
{previous_summary}

Messages to compress:
{messages_block}

Write an updated running summary that replaces the previous summary and covers the new messages.
"""


def render_compaction_user(*, previous_summary: str, messages_block: str) -> str:
    return COMPACTION_USER_TEMPLATE.format(
        previous_summary=(previous_summary or "(none)").strip(),
        messages_block=(messages_block or "(none)").strip(),
    )
