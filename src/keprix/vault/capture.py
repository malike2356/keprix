"""Auto-capture conversations into the single markdown vault.

Prompt 270 Phase 1: every conversation becomes a vault note so agents share
one memory (Capture → Store → Read → Visualize).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from keprix.research_workspace.obsidian.frontmatter import dump_frontmatter
from keprix.vault.config import VaultConfig, get_configured_provider, get_vault_config, save_vault_config
from keprix_constants import get_keprix_home

logger = logging.getLogger(__name__)

CAPTURE_DIR = "conversations"
DEFAULT_VAULT_REL = "vault"


def auto_capture_enabled() -> bool:
    raw = os.getenv("KEPRIX_VAULT_AUTO_CAPTURE", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def ensure_default_vault() -> VaultConfig:
    """Enforce the one-vault rule: create ~/.keprix/vault when unset."""
    config = get_vault_config()
    if config.root_path:
        return config
    root = get_keprix_home() / DEFAULT_VAULT_REL
    root.mkdir(parents=True, exist_ok=True)
    (root / CAPTURE_DIR).mkdir(parents=True, exist_ok=True)
    return save_vault_config(
        VaultConfig(provider="local_folder", root_path=str(root), watch=True, read_only=False)
    )


def _slug(value: str, *, fallback: str = "conversation") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", (value or "").strip().lower()).strip("-")
    return (cleaned[:80] or fallback)


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = str(block.get("content") or "").strip()
                if text:
                    parts.append(text)
            elif isinstance(block, dict) and block.get("type") == "tool_call":
                name = str(block.get("name") or "tool")
                parts.append(f"[tool:{name}]")
        return "\n".join(parts).strip()
    return ""


def _title_from_messages(messages: list[dict[str, Any]], fallback: str) -> str:
    for message in messages:
        if str(message.get("role") or "") != "user":
            continue
        text = _message_text(message)
        if text:
            first_line = text.splitlines()[0].strip()
            return first_line[:120] or fallback
    return fallback


def render_conversation_note(
    *,
    session_id: str,
    messages: list[dict[str, Any]],
    title: str | None = None,
    source: str = "web",
    agent_id: str | None = None,
) -> tuple[str, str]:
    """Return (relative_path, markdown_content) for a conversation note."""
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y/%m")
    safe_id = _slug(session_id, fallback="session")
    path = f"{CAPTURE_DIR}/{stamp}/{safe_id}.md"
    resolved_title = title or _title_from_messages(messages, f"Conversation {safe_id}")
    meta: dict[str, Any] = {
        "title": resolved_title,
        "type": "conversation",
        "session_id": session_id,
        "source": source,
        "captured_at": now.isoformat(),
        "message_count": len(messages),
        "tags": ["conversation", "auto-capture"],
    }
    if agent_id:
        meta["agent_id"] = agent_id

    body_lines = [f"# {resolved_title}", "", f"Session `{session_id}` captured from `{source}`.", ""]
    for message in messages:
        role = str(message.get("role") or "unknown").upper()
        text = _message_text(message)
        if not text:
            continue
        body_lines.append(f"## {role}")
        body_lines.append("")
        body_lines.append(text)
        body_lines.append("")
    content = dump_frontmatter(meta, "\n".join(body_lines).rstrip() + "\n")
    return path, content


async def capture_conversation(
    *,
    session_id: str,
    messages: list[dict[str, Any]],
    title: str | None = None,
    source: str = "web",
    agent_id: str | None = None,
    ensure_vault: bool = True,
) -> dict[str, Any]:
    """Write or refresh one markdown note for this conversation in the vault."""
    if not auto_capture_enabled():
        return {"ok": False, "skipped": True, "reason": "auto_capture_disabled"}
    if ensure_vault:
        ensure_default_vault()
    try:
        provider = get_configured_provider()
    except ValueError as exc:
        return {"ok": False, "skipped": True, "reason": str(exc)}

    config = get_vault_config()
    if config.read_only:
        return {"ok": False, "skipped": True, "reason": "vault_read_only"}

    path, content = render_conversation_note(
        session_id=session_id,
        messages=messages,
        title=title,
        source=source,
        agent_id=agent_id,
    )
    await provider.write_file(path, content)
    try:
        from keprix.agent_os.guardrails import maybe_backup_vault_before_write

        # Snapshot after successful write so the note is included; throttle via env.
        if os.getenv("KEPRIX_VAULT_BACKUP_EVERY_CAPTURE", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            maybe_backup_vault_before_write()
    except Exception:
        logger.debug("vault backup after capture skipped", exc_info=True)
    return {
        "ok": True,
        "path": path,
        "session_id": session_id,
        "message_count": len(messages),
        "vault_root": config.root_path,
    }


def capture_conversation_sync(**kwargs: Any) -> dict[str, Any]:
    """Sync wrapper for CLI and gateway hooks."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(capture_conversation(**kwargs))

    # Already inside an event loop: schedule and return a pending marker.
    future = asyncio.ensure_future(capture_conversation(**kwargs))

    def _log_result(task: Any) -> None:
        try:
            result = task.result()
            if result.get("ok"):
                logger.debug("vault capture wrote %s", result.get("path"))
            else:
                logger.debug("vault capture skipped: %s", result.get("reason"))
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("vault capture failed: %s", exc)

    future.add_done_callback(_log_result)
    return {"ok": True, "scheduled": True, "session_id": kwargs.get("session_id")}
