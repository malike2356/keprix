"""Aiva session compaction: summarize older turns, keep recent raw messages."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from keprix.aiva.compaction_prompts import COMPACTION_SYSTEM, render_compaction_user

logger = logging.getLogger(__name__)

Summarizer = Callable[[str, str], str]

DEFAULT_THRESHOLD = 20
DEFAULT_BATCH_SIZE = 20
DEFAULT_KEEP_RECENT = 20
DEFAULT_MODEL = "deepseek-chat"
SUMMARY_ROLE = "system"
SUMMARY_MARKER = "[aiva-session-summary]"


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def compaction_settings() -> dict[str, Any]:
    return {
        "threshold": _env_int("AIVA_COMPACTION_THRESHOLD", DEFAULT_THRESHOLD),
        "batch_size": _env_int("AIVA_COMPACTION_BATCH_SIZE", DEFAULT_BATCH_SIZE),
        "keep_recent": _env_int("AIVA_COMPACTION_KEEP_RECENT", DEFAULT_KEEP_RECENT),
        "model": (os.getenv("AIVA_COMPACTION_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL,
    }


def _message_text(msg: Mapping[str, Any]) -> str:
    content = msg.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, Mapping) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(p for p in parts if p).strip()
    return str(content or "").strip()


def is_summary_message(msg: Mapping[str, Any]) -> bool:
    if str(msg.get("role") or "").lower() != SUMMARY_ROLE:
        return False
    text = _message_text(msg)
    return text.startswith(SUMMARY_MARKER) or bool(msg.get("aiva_summary"))


def extract_previous_summary(messages: Sequence[Mapping[str, Any]]) -> str:
    for msg in messages:
        if not is_summary_message(msg):
            continue
        text = _message_text(msg)
        if text.startswith(SUMMARY_MARKER):
            return text[len(SUMMARY_MARKER) :].lstrip(" \n:")
        return text
    return ""


def _format_messages_block(messages: Sequence[Mapping[str, Any]]) -> str:
    lines: list[str] = []
    for msg in messages:
        role = str(msg.get("role") or "unknown")
        if role == "tool":
            name = str(msg.get("name") or "tool")
            body = _message_text(msg)
            if len(body) > 400:
                body = body[:400] + "..."
            lines.append(f"[tool:{name}] {body}")
            continue
        body = _message_text(msg)
        if not body and msg.get("tool_calls"):
            body = f"(tool_calls={len(msg.get('tool_calls') or [])})"
        if len(body) > 800:
            body = body[:800] + "..."
        lines.append(f"{role}: {body}")
    return "\n".join(lines)


def extractive_summary(*, previous_summary: str, messages: Sequence[Mapping[str, Any]]) -> str:
    """Fallback summarizer when no LLM is available."""
    bits: list[str] = []
    if previous_summary.strip():
        bits.append(previous_summary.strip())
    for msg in messages:
        role = str(msg.get("role") or "")
        if role not in {"user", "assistant"}:
            continue
        text = _message_text(msg)
        if not text:
            continue
        snippet = text.replace("\n", " ").strip()
        if len(snippet) > 180:
            snippet = snippet[:180] + "..."
        bits.append(f"{role}: {snippet}")
    joined = " | ".join(bits)
    if len(joined) > 1800:
        joined = joined[:1800].rstrip() + "..."
    return joined or "No prior conversation details retained."


def default_llm_summarizer(system: str, user: str) -> str:
    """Call the cheap compaction model; raise on failure so caller can fall back."""
    settings = compaction_settings()
    model = settings["model"]
    # Prefer DeepSeek OpenAI-compatible path when configured.
    api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set for Aiva compaction")
    try:
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("openai package unavailable") from exc

    client = OpenAI(api_key=api_key, base_url=os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=800,
    )
    content = (resp.choices[0].message.content or "").strip()
    if not content:
        raise RuntimeError("empty compaction response")
    return content


def maybe_compact_messages(
    messages: list[dict[str, Any]],
    *,
    summarizer: Summarizer | None = None,
    threshold: int | None = None,
    batch_size: int | None = None,
    keep_recent: int | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """
    If raw (non-summary) messages exceed threshold, summarize the oldest batch
    and keep the most recent keep_recent messages plus one summary system message.
    """
    settings = compaction_settings()
    threshold = int(threshold if threshold is not None else settings["threshold"])
    batch_size = int(batch_size if batch_size is not None else settings["batch_size"])
    keep_recent = int(keep_recent if keep_recent is not None else settings["keep_recent"])

    if not messages:
        return messages, False

    previous = extract_previous_summary(messages)
    working = [dict(m) for m in messages if not is_summary_message(m)]
    if len(working) <= threshold:
        return messages, False

    # Compact oldest overflow beyond keep_recent, at least batch_size when possible.
    overflow = max(0, len(working) - keep_recent)
    take = min(len(working) - keep_recent, max(batch_size, overflow)) if overflow else 0
    if take <= 0:
        return messages, False

    to_summarize = working[:take]
    retained = working[take:]
    user_prompt = render_compaction_user(
        previous_summary=previous,
        messages_block=_format_messages_block(to_summarize),
    )
    summarize = summarizer or default_llm_summarizer
    try:
        summary_text = summarize(COMPACTION_SYSTEM, user_prompt).strip()
    except Exception as exc:
        logger.warning("Aiva compaction LLM failed (%s); using extractive fallback", exc)
        summary_text = extractive_summary(previous_summary=previous, messages=to_summarize)

    summary_msg: dict[str, Any] = {
        "role": SUMMARY_ROLE,
        "content": f"{SUMMARY_MARKER}\n{summary_text}".strip(),
        "aiva_summary": True,
    }
    compacted = [summary_msg, *retained]
    return compacted, True


async def maybe_compact_session_store(
    session_store: Any,
    workspace_id: str,
    session_id: str,
    *,
    summarizer: Summarizer | None = None,
) -> bool:
    """Load, compact, and persist session messages when over threshold."""
    if not session_store or not workspace_id or not session_id:
        return False
    try:
        messages = list(await session_store.get(workspace_id, session_id) or [])
    except Exception as exc:
        logger.warning(
            "Aiva compaction load failed for %s/%s: %s", workspace_id, session_id, exc
        )
        return False
    compacted, changed = maybe_compact_messages(messages, summarizer=summarizer)
    if not changed:
        return False
    try:
        await session_store.save(workspace_id, session_id, compacted)
    except Exception as exc:
        logger.warning(
            "Aiva compaction save failed for %s/%s: %s", workspace_id, session_id, exc
        )
        return False
    return True
