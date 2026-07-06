"""Execute slash commands with permissions, confirmations, and audit."""

from __future__ import annotations

import uuid
from typing import Any

from keprix.slash.audit import get_slash_audit_store
from keprix.slash.confirmations import get_confirmation_store, get_cyber_authorization_store
from keprix.slash.parser import parse_slash
from keprix.slash.permissions import default_role_for_channel, normalize_role, role_allows
from keprix.slash.registry import get_slash_registry
from keprix.slash.schemas import SlashContext, SlashResult


async def _execute_confirmed_action(ctx: SlashContext, data: dict[str, Any]) -> SlashResult:
    action = data.get("action")
    if action == "memory.save":
        from keprix.memory.episodic.store import create_episodic_store

        store = create_episodic_store()
        memory_id = await store.save(ctx.user_id, str(data.get("content", "")))
        return SlashResult(ok=True, message=f"Memory saved: {memory_id}")
    if action == "playbook.serve":
        from keprix.playbook.jobs import get_playbook_job_store
        from keprix.playbook.model_catalog import get_model

        model_id = str(data.get("model") or "")
        if get_model(model_id) is None:
            return SlashResult(ok=False, message=f"Unknown playbook model `{model_id}`.")
        job_store = get_playbook_job_store()
        port = 11434
        job_store.register_serving(model_id, "ollama", port)
        job = job_store.create(user_id=ctx.user_id, job_type="serve", model_id=model_id)
        job.status = "complete"
        job.completed_at = job.started_at
        job.result = {"port": port, "backend": "ollama"}
        job_store.append_log(job, f"Registered {model_id} on ollama port {port}")
        return SlashResult(
            ok=True,
            message=f"Registered local backend for `{model_id}` on port {port}.",
            data={"job_id": job.id, "model_id": model_id, "port": port},
        )
    if action == "tool.run":
        from keprix.tools.registry import registry

        tool_name = str(data.get("tool") or "")
        args = data.get("args") or {}
        if not registry.get_entry(tool_name):
            return SlashResult(ok=False, message=f"Tool `{tool_name}` is not registered.")
        try:
            output = registry.dispatch(tool_name, args)
            return SlashResult(
                ok=True,
                message=f"Tool `{tool_name}` completed.",
                data={"tool": tool_name, "output": output},
            )
        except Exception as exc:
            return SlashResult(ok=False, message=f"Tool `{tool_name}` failed: {exc}")
    if action == "research.start":
        from keprix.research.pipeline import schedule_research_job
        from keprix.research.store import get_research_store

        query = str(data.get("query") or "").strip()
        if not query:
            return SlashResult(ok=False, message="Research query is required.")
        depth = str(data.get("depth") or "standard").strip().lower()
        if depth not in {"quick", "standard", "deep"}:
            return SlashResult(ok=False, message="Depth must be quick, standard, or deep.")
        model = data.get("model")
        store = get_research_store()
        job = await store.create(
            user_id=ctx.user_id,
            query=query,
            depth=depth,
            model=str(model) if model else None,
        )
        schedule_research_job(job)
        return SlashResult(
            ok=True,
            message=f"Research job `{job.id}` started.",
            data={"job_id": job.id, "status": "running", "query": query, "depth": depth},
        )
    if action == "settings.set":
        import contextlib
        import io

        from keprix_cli.config import set_config_value

        key = str(data.get("key") or "")
        value = data.get("value")
        if not key:
            return SlashResult(ok=False, message="Setting key is required.")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            set_config_value(key, str(value))
        detail = buffer.getvalue().strip()
        return SlashResult(
            ok=True,
            message=detail or f"Setting `{key}` updated.",
            data={"key": key, "value": value},
        )
    return SlashResult(ok=True, message="Action completed.", data=data)


def build_context(
    *,
    raw_text: str,
    user_id: str,
    workspace_id: str,
    channel: str,
    channel_user_id: str,
    metadata: dict[str, Any] | None = None,
    role: str | None = None,
    request_id: str | None = None,
    skip_confirmation: bool = False,
    confirmation_token: str | None = None,
) -> SlashContext:
    registry = get_slash_registry()
    parsed = parse_slash(raw_text, registry.names())
    resolved_role = normalize_role(role or default_role_for_channel(channel, metadata))
    return SlashContext(
        user_id=user_id,
        workspace_id=workspace_id,
        channel=channel,
        channel_user_id=channel_user_id,
        raw_text=raw_text,
        command=parsed.command,
        args=parsed.args,
        flags=parsed.flags,
        json_args=parsed.json_args,
        metadata=metadata or {},
        request_id=request_id or str(uuid.uuid4()),
        role=resolved_role,
        skip_confirmation=skip_confirmation,
        confirmation_token=confirmation_token,
    )


async def execute_context(ctx: SlashContext) -> SlashResult:
    registry = get_slash_registry()
    audit = get_slash_audit_store()
    parsed = parse_slash(ctx.raw_text, registry.names())

    if parsed.unknown or not parsed.command:
        suggestions = ", ".join(parsed.suggestions) if parsed.suggestions else "none"
        audit_id = audit.write(
            workspace_id=ctx.workspace_id,
            user_id=ctx.user_id,
            channel=ctx.channel,
            command=parsed.command or "unknown",
            args={"raw": ctx.raw_text},
            status="unknown",
            risk_level="low",
        )
        return SlashResult(
            ok=False,
            message=f"Unknown command `/{parsed.command or ''}`. Did you mean: {suggestions}?",
            audit_id=audit_id,
        )

    command = registry.get(parsed.command)
    if command is None or command.handler is None:
        audit_id = audit.write(
            workspace_id=ctx.workspace_id,
            user_id=ctx.user_id,
            channel=ctx.channel,
            command=parsed.command,
            args={"args": parsed.args, "flags": parsed.flags},
            status="unknown",
        )
        return SlashResult(ok=False, message=f"Command `/{parsed.command}` is not registered.", audit_id=audit_id)

    if command.cyber_scoped and not get_cyber_authorization_store().is_active(ctx.workspace_id, ctx.user_id):
        audit_id = audit.write(
            workspace_id=ctx.workspace_id,
            user_id=ctx.user_id,
            channel=ctx.channel,
            command=command.name,
            args={"args": parsed.args},
            status="blocked",
            risk_level="high",
            error="cyber authorization required",
        )
        return SlashResult(
            ok=False,
            message="Cyber command blocked: no active authorization record.",
            audit_id=audit_id,
        )

    if not role_allows(ctx.role, command.min_role):
        audit_id = audit.write(
            workspace_id=ctx.workspace_id,
            user_id=ctx.user_id,
            channel=ctx.channel,
            command=command.name,
            args={"args": parsed.args},
            status="denied",
            risk_level=command.risk_level,
            error="insufficient role",
        )
        return SlashResult(ok=False, message=f"Permission denied for `/{command.name}` (requires {command.min_role}).", audit_id=audit_id)

    handler_ctx = SlashContext(
        user_id=ctx.user_id,
        workspace_id=ctx.workspace_id,
        channel=ctx.channel,
        channel_user_id=ctx.channel_user_id,
        raw_text=ctx.raw_text,
        command=command.name,
        args=parsed.args,
        flags=parsed.flags,
        json_args=parsed.json_args,
        metadata=ctx.metadata,
        request_id=ctx.request_id,
        role=ctx.role,
        skip_confirmation=ctx.skip_confirmation,
        confirmation_token=ctx.confirmation_token,
    )
    result = await command.handler(handler_ctx)

    needs_confirmation = result.requires_confirmation or command.requires_confirmation
    if needs_confirmation and not ctx.skip_confirmation:
        token, token_hash = get_confirmation_store().create(
            command=command.name,
            context={
                "raw_text": ctx.raw_text,
                "args": parsed.args,
                "flags": parsed.flags,
                "json_args": parsed.json_args,
                "data": result.data,
            },
            user_id=ctx.user_id,
            workspace_id=ctx.workspace_id,
            role=ctx.role,
            preview=result.message,
            risk_level=command.risk_level,
        )
        audit_id = audit.write(
            workspace_id=ctx.workspace_id,
            user_id=ctx.user_id,
            channel=ctx.channel,
            command=command.name,
            args={"args": parsed.args, "flags": parsed.flags, "data": result.data},
            status="pending",
            risk_level=command.risk_level,
            confirmation_required=True,
            confirmation_token_hash=token_hash,
        )
        return SlashResult(
            ok=True,
            message=result.message + f"\nApprove with `/approve {token}` or cancel with `/cancel {token}`.",
            requires_confirmation=True,
            confirmation_token=token,
            audit_id=audit_id,
            ephemeral=result.ephemeral,
            blocks=result.blocks,
            data=result.data,
        )

    audit_id = audit.write(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        channel=ctx.channel,
        command=command.name,
        args={"args": parsed.args, "flags": parsed.flags, "data": result.data},
        status="completed" if result.ok else "failed",
        risk_level=command.risk_level,
        error=None if result.ok else result.message,
    )
    result.audit_id = audit_id
    return result


async def approve_token(ctx: SlashContext, token: str) -> SlashResult:
    store = get_confirmation_store()
    pending = store.get(token)
    audit = get_slash_audit_store()
    if not pending:
        audit_id = audit.write(
            workspace_id=ctx.workspace_id,
            user_id=ctx.user_id,
            channel=ctx.channel,
            command="approve",
            args={"token": "[redacted]"},
            status="failed",
            error="invalid or expired token",
        )
        return SlashResult(ok=False, message="Invalid or expired confirmation token.", audit_id=audit_id)
    if pending.executed:
        return SlashResult(ok=False, message="Confirmation token already used.")
    if pending.user_id != ctx.user_id and ctx.role not in {"admin", "owner"}:
        return SlashResult(ok=False, message="Only the requesting user or an admin can approve this command.")

    store.mark_executed(token)
    action_ctx = SlashContext(
        user_id=ctx.user_id,
        workspace_id=ctx.workspace_id,
        channel=ctx.channel,
        channel_user_id=ctx.channel_user_id,
        raw_text=pending.context.get("raw_text", ""),
        command=pending.command,
        args=list(pending.context.get("args") or []),
        flags=dict(pending.context.get("flags") or {}),
        json_args=pending.context.get("json_args"),
        metadata=ctx.metadata,
        request_id=ctx.request_id,
        role=ctx.role,
        skip_confirmation=True,
    )
    data = dict(pending.context.get("data") or {})
    result = await _execute_confirmed_action(action_ctx, data)
    audit_id = audit.write(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        channel=ctx.channel,
        command=pending.command,
        args={"approved": True, "data": data},
        status="completed" if result.ok else "failed",
        risk_level=pending.risk_level,
        confirmation_required=True,
        confirmation_token_hash=pending.token_hash,
    )
    result.audit_id = audit_id
    result.message = f"Approved.\n{result.message}"
    return result


async def cancel_token(ctx: SlashContext, token: str) -> SlashResult:
    store = get_confirmation_store()
    pending = store.get(token)
    if not pending:
        return SlashResult(ok=False, message="Invalid or expired confirmation token.")
    if pending.user_id != ctx.user_id and ctx.role not in {"admin", "owner"}:
        return SlashResult(ok=False, message="Only the requesting user or an admin can cancel this command.")
    store.cancel(token)
    audit_id = get_slash_audit_store().write(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        channel=ctx.channel,
        command=pending.command,
        args={"cancelled": True},
        status="rejected",
        risk_level=pending.risk_level,
        confirmation_required=True,
        confirmation_token_hash=pending.token_hash,
    )
    return SlashResult(ok=True, message="Pending command cancelled.", audit_id=audit_id)
