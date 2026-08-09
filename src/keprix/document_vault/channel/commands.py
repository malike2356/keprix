"""Discoverable /vault channel commands and natural-language helpers (Prompt 651)."""

from __future__ import annotations

import base64
import re
from typing import Any

from keprix.document_vault.channel.binding import (
    bind_channel_identity,
    resolve_channel_binding,
    revoke_channel_binding,
    tool_kwargs_from_binding,
)
from keprix.document_vault.channel.contract import ChannelAttachment
from keprix.document_vault.channel.export_delivery import plan_export_delivery
from keprix.document_vault.channel.import_pipeline import import_channel_attachment
from keprix.document_vault.models import VaultError
from keprix.document_vault.store import get_document_vault_store
from keprix.slash.schemas import SlashContext, SlashResult
from keprix.tools import document_vault_tools as dvt

_USAGE = (
    "Usage: /vault status | list | search <q> | mkdir <name> | create <name> [text] | "
    "rename <id> <name> | move <id> [parent] | export <id> [format] | sync | "
    "bind <workspace_id> | revoke | help"
)


def parse_vault_nl(text: str) -> dict[str, Any] | None:
    """Map short natural-language vault intents to command args."""
    raw = (text or "").strip()
    lower = raw.lower()
    if lower in {"list vault", "show vault", "vault list"}:
        return {"sub": "list"}
    if lower.startswith("search vault ") or lower.startswith("find in vault "):
        q = raw.split(" ", 2)[-1] if " " in raw else ""
        return {"sub": "search", "args": [q]} if q else None
    if lower.startswith("save to vault") or lower.startswith("import to vault"):
        return {"sub": "import"}
    if lower.startswith("summarize vault") or lower == "summarize vault":
        return {"sub": "summarize"}
    return None


async def handle_vault_channel_command(ctx: SlashContext) -> SlashResult:
    text = ctx.raw_text or f"/{ctx.command} {' '.join(ctx.args)}"
    parts = (text or "").strip().split()
    # /vault ...  or vault ...
    if parts and parts[0].lstrip("/").split("@", 1)[0].lower() == "vault":
        parts = parts[1:]
    elif ctx.args:
        parts = list(ctx.args)

    if not parts:
        nl = parse_vault_nl(ctx.metadata.get("nl_text") or "")
        if nl:
            parts = [nl["sub"], *list(nl.get("args") or [])]
        else:
            return SlashResult(ok=True, message=_USAGE)

    sub = str(parts[0]).lower().lstrip("/")
    rest = parts[1:]

    if sub in {"help", "?"}:
        return SlashResult(ok=True, message=_USAGE)

    # Bind/revoke are privileged channel admin ops (no vault content access yet).
    if sub == "bind":
        if not rest:
            return SlashResult(ok=False, message="Usage: /vault bind <workspace_id>")
        if ctx.role not in {"admin", "owner", "operator"}:
            return SlashResult(ok=False, message="Denied: admin/operator role required to bind.")
        try:
            row = bind_channel_identity(
                workspace_id=rest[0],
                platform=ctx.channel,
                channel_user_id=ctx.channel_user_id or ctx.user_id,
                actor_id=ctx.user_id,
            )
        except VaultError as exc:
            return SlashResult(ok=False, message=f"{exc.code}: {exc.message}")
        return SlashResult(ok=True, message=f"Bound {ctx.channel}:{ctx.channel_user_id} -> workspace {row.get('workspace_id')}")

    if sub == "revoke":
        if ctx.role not in {"admin", "owner", "operator"}:
            return SlashResult(ok=False, message="Denied: admin/operator role required to revoke.")
        revoke_channel_binding(ctx.channel, ctx.channel_user_id or ctx.user_id)
        return SlashResult(ok=True, message="Channel Document Vault binding revoked.")

    try:
        vault_ctx = resolve_channel_binding(
            ctx.channel,
            ctx.channel_user_id or ctx.user_id,
            # Never trust slash workspace_id as binding source; only verify mismatch.
            claimed_workspace_id=None,
        )
    except VaultError as exc:
        return SlashResult(ok=False, message=f"{exc.code}: {exc.message}. Use /vault bind <workspace_id> (admin).")

    kw = tool_kwargs_from_binding(vault_ctx)

    try:
        if sub == "status":
            return SlashResult(
                ok=True,
                message=(
                    f"Document Vault channel ok. workspace={vault_ctx.workspace_id} "
                    f"actor={vault_ctx.actor_id} channel={vault_ctx.channel}"
                ),
                data=vault_ctx.as_dict(),
            )
        if sub == "list":
            payload = dvt.document_vault_list({"limit": 20}, **kw)
            return _tool_result(payload, prefix="Vault list")
        if sub == "search":
            q = " ".join(rest).strip()
            if not q:
                return SlashResult(ok=False, message="Usage: /vault search <query>")
            payload = dvt.document_vault_search({"q": q, "limit": 20}, **kw)
            return _tool_result(payload, prefix=f"Search `{q}`")
        if sub == "summarize":
            payload = dvt.document_vault_list({"limit": 10}, **kw)
            import json

            data = json.loads(payload)
            items = data.get("items") or []
            lines = [f"- {row.get('name')} ({row.get('kind')}) id={row.get('id')}" for row in items]
            body = "\n".join(lines) if lines else "(empty)"
            return SlashResult(ok=True, message=f"Vault summary ({len(items)} items):\n{body}")
        if sub in {"mkdir", "folder"}:
            name = " ".join(rest).strip()
            if not name:
                return SlashResult(ok=False, message="Usage: /vault mkdir <name>")
            payload = dvt.document_vault_create_folder({"name": name}, **kw)
            return _tool_result(payload, prefix="Created folder")
        if sub in {"create", "new", "write"}:
            if not rest:
                return SlashResult(ok=False, message="Usage: /vault create <name> [content]")
            name = rest[0]
            content = " ".join(rest[1:]) if len(rest) > 1 else ""
            payload = dvt.document_vault_create_file({"name": name, "content": content}, **kw)
            return _tool_result(payload, prefix="Created file")
        if sub == "rename":
            if len(rest) < 2:
                return SlashResult(ok=False, message="Usage: /vault rename <item_id> <name>")
            payload = dvt.document_vault_rename({"item_id": rest[0], "name": " ".join(rest[1:])}, **kw)
            return _tool_result(payload, prefix="Renamed")
        if sub == "move":
            if not rest:
                return SlashResult(ok=False, message="Usage: /vault move <item_id> [parent_id]")
            args = {"item_id": rest[0]}
            if len(rest) > 1:
                args["parent_id"] = rest[1]
            payload = dvt.document_vault_move(args, **kw)
            return _tool_result(payload, prefix="Moved")
        if sub == "export":
            if not rest:
                return SlashResult(ok=False, message="Usage: /vault export <item_id> [format]")
            item_id = rest[0]
            fmt = rest[1] if len(rest) > 1 else "markdown"
            planned = plan_export_delivery(vault_ctx, item_id, fmt=fmt)
            if planned.get("blocked"):
                return SlashResult(
                    ok=False,
                    message="Soft Wall required for classified export.",
                    data=planned,
                )
            if planned.get("mode") == "url":
                return SlashResult(ok=True, message=planned.get("receipt") + f"\n{planned.get('download_url')}", data=planned)
            return SlashResult(ok=True, message=planned.get("receipt") or "Export ready", data=planned)
        if sub == "sync":
            payload = dvt.document_vault_sync_status({}, **kw)
            return _tool_result(payload, prefix="Sync status")
        if sub == "import":
            att = _attachment_from_metadata(ctx, vault_ctx.channel)
            if not att:
                return SlashResult(
                    ok=False,
                    message="No attachment on this message. Send a file with caption /vault import",
                )
            parent = None
            for i, tok in enumerate(rest):
                if tok in {"--parent", "-p"} and i + 1 < len(rest):
                    parent = rest[i + 1]
            receipt = import_channel_attachment(att, parent_id=parent)
            return SlashResult(
                ok=receipt.ok,
                message=receipt.message,
                data={"item_id": receipt.item_id, "job_id": receipt.job_id, "deduplicated": receipt.deduplicated, **receipt.data},
            )
        if sub == "update":
            if len(rest) < 2:
                return SlashResult(ok=False, message="Usage: /vault update <item_id> <content>")
            payload = dvt.document_vault_update({"item_id": rest[0], "content": " ".join(rest[1:])}, **kw)
            return _tool_result(payload, prefix="Updated")
    except VaultError as exc:
        return SlashResult(ok=False, message=f"{exc.code}: {exc.message}", data=exc.extra or {})
    except Exception as exc:
        return SlashResult(ok=False, message=str(exc))

    return SlashResult(ok=False, message=_USAGE)


def _tool_result(payload: str, *, prefix: str) -> SlashResult:
    import json

    try:
        data = json.loads(payload)
    except Exception:
        return SlashResult(ok=False, message=payload)
    if not data.get("ok", True) and data.get("error_code"):
        return SlashResult(ok=False, message=f"{data.get('error_code')}: {data.get('error')}", data=data)
    item = data.get("item")
    if item:
        return SlashResult(
            ok=True,
            message=f"{prefix}: {item.get('name')} id={item.get('id')} rev={item.get('current_revision')}",
            data=data,
        )
    items = data.get("items") or []
    if items:
        lines = [f"- {row.get('name')} ({row.get('kind')}) `{row.get('id')}`" for row in items[:15]]
        return SlashResult(ok=True, message=f"{prefix} ({len(items)}):\n" + "\n".join(lines), data=data)
    return SlashResult(ok=True, message=f"{prefix}: {payload[:500]}", data=data if isinstance(data, dict) else {})


def _attachment_from_metadata(ctx: SlashContext, platform: str) -> ChannelAttachment | None:
    meta = ctx.metadata or {}
    raw_b64 = meta.get("attachment_base64") or meta.get("file_base64")
    filename = meta.get("attachment_filename") or meta.get("filename") or "upload.bin"
    event_id = str(meta.get("event_id") or meta.get("message_id") or ctx.request_id or "").strip()
    if not raw_b64 or not event_id:
        return None
    try:
        data = base64.b64decode(raw_b64)
    except Exception:
        return None
    return ChannelAttachment(
        platform=platform,
        channel_user_id=ctx.channel_user_id or ctx.user_id,
        event_id=event_id,
        filename=str(filename),
        data=data,
        declared_mime=str(meta.get("mime") or meta.get("content_type") or ""),
        caption=ctx.raw_text or "",
    )


def looks_like_vault_import_caption(text: str | None) -> bool:
    raw = (text or "").strip().lower()
    if not raw:
        return False
    if raw.startswith("/vault import") or raw.startswith("vault import"):
        return True
    return bool(re.search(r"\b(save|import)\s+(this\s+)?(to\s+)?vault\b", raw))


__all__ = [
    "handle_vault_channel_command",
    "looks_like_vault_import_caption",
    "parse_vault_nl",
]
