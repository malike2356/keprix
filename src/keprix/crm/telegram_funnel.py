"""Telegram / channel funnel intents for CRM Soft Wall (prompt 446)."""

from __future__ import annotations

import re
from typing import Any

from keprix.slash.schemas import SlashContext, SlashResult

# Linked workspace authz: deny strangers (no workspace match / anonymous)
def assert_channel_authz(ctx: SlashContext) -> SlashResult | None:
    user = str(ctx.user_id or "").strip()
    channel_user = str(ctx.channel_user_id or "").strip()
    if not user or user in {"anonymous", "stranger", "unknown"}:
        return SlashResult(ok=False, message="Denied: link your Telegram account to a Keprix workspace user first.")
    # Soft check: workspace must be present
    if not str(ctx.workspace_id or "").strip():
        return SlashResult(ok=False, message="Denied: no workspace bound to this chat.")
    # Role gate for CRM mutations
    if ctx.role in {"viewer"} and ctx.command in {"leads.approve", "leads.find"}:
        # find is ok for operator+; approve needs operator
        pass
    return None


def parse_leads_intent(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    lower = raw.lower()
    # Natural language
    m = re.search(r"find\s+(.+?)\s+in\s+([a-zA-Z\s]+)$", lower)
    if m:
        return {"intent": "find", "query": m.group(1).strip(), "location": m.group(2).strip()}
    if lower.startswith("/leads") or lower.startswith("leads "):
        parts = raw.split()
        # /leads find plumbers in Leeds
        if len(parts) >= 2:
            sub = parts[1].lower().lstrip("/")
            rest = " ".join(parts[2:]).strip()
            if sub == "find":
                loc = None
                query = rest
                if " in " in rest.lower():
                    q, _, loc = rest.partition(" in ")
                    if not loc:
                        q, _, loc = rest.partition(" In ")
                    query, loc = q.strip(), loc.strip()
                return {"intent": "find", "query": query, "location": loc}
            if sub == "approve":
                return {"intent": "approve", "approval_id": rest or None}
            if sub == "digest":
                return {"intent": "digest", "period": rest or "daily"}
            if sub == "reject":
                return {"intent": "reject", "approval_id": rest or None}
    if lower.startswith("/crm") or lower.startswith("crm "):
        parts = raw.split(maxsplit=2)
        sub = parts[1].lower() if len(parts) > 1 else ""
        rest = parts[2] if len(parts) > 2 else ""
        if sub == "ask":
            return {"intent": "crm_ask", "question": rest}
    return None


async def handle_leads_command(ctx: SlashContext) -> SlashResult:
    denied = assert_channel_authz(ctx)
    if denied:
        return denied

    # Rebuild text for parser
    text = ctx.raw_text or f"/{ctx.command} {' '.join(ctx.args)}"
    parsed = parse_leads_intent(text)
    if not parsed and ctx.args:
        sub = str(ctx.args[0]).lower()
        rest = " ".join(ctx.args[1:])
        parsed = parse_leads_intent(f"/leads {sub} {rest}")
    if not parsed:
        return SlashResult(
            ok=False,
            message="Usage: /leads find <query> [in place] | /leads approve <id> | /leads digest | /crm ask <question>",
        )

    ws = ctx.workspace_id
    intent = parsed["intent"]

    if intent == "find":
        if ctx.role not in {"operator", "admin", "owner", "user"} and ctx.role == "viewer":
            return SlashResult(ok=False, message="Denied: operator role required to start discovery.")
        query = parsed.get("query") or ""
        location = parsed.get("location")
        try:
            from keprix.discovery.service import get_discovery_service  # type: ignore
        except Exception:
            get_discovery_service = None  # type: ignore
        job = None
        try:
            from keprix.crm.store import get_crm_store

            store = get_crm_store()
            # Create discovery job record when available
            if hasattr(store, "create_discovery_job"):
                job = store.create_discovery_job(
                    ws,
                    adapter="generic",
                    params={"q": query, "location": location, "source": "telegram"},
                    status="queued",
                    actor_type="user",
                    actor_id=ctx.user_id,
                )
            else:
                job = {"id": "pending", "params": {"q": query, "location": location}}
            # Soft Wall before enroll is documented; discovery itself may Soft Wall on materialize
            return SlashResult(
                ok=True,
                message=(
                    f"Discovery queued for '{query}'"
                    + (f" in {location}" if location else "")
                    + f". Soft Wall required before list enroll. Job: {(job or {}).get('id')}. Open /crm/jobs"
                ),
                data={"job": job, "deep_link": f"/crm/jobs/{(job or {}).get('id')}"},
            )
        except Exception as exc:
            return SlashResult(ok=True, message=f"Could not start discovery: {exc}")

    if intent == "approve":
        if ctx.role in {"viewer"}:
            return SlashResult(ok=False, message="Denied: approve requires operator.")
        approval_id = parsed.get("approval_id") or (ctx.args[1] if len(ctx.args) > 1 else "")
        if not approval_id:
            # List pending
            from keprix.crm.soft_wall import pending_crm_approvals

            items = pending_crm_approvals(ws)
            if not items:
                return SlashResult(ok=True, message="No pending Soft Wall CRM approvals.")
            lines = [f"- {i.get('id')}: {i.get('subject') or i.get('approval_kind')}" for i in items[:10]]
            return SlashResult(
                ok=True,
                message="Pending Soft Wall:\n" + "\n".join(lines) + "\nApprove with /leads approve <id>",
            )
        from keprix.crm.soft_wall import resolve_crm_approval

        row = resolve_crm_approval(ws, str(approval_id), status="approved")
        if not row:
            return SlashResult(ok=False, message="Approval not found for this workspace.")
        return SlashResult(
            ok=True,
            message=f"Approved Soft Wall item {approval_id}. Confirm enroll/enrich in /crm if needed.",
            data={"approval": row},
        )

    if intent == "reject":
        approval_id = parsed.get("approval_id") or (ctx.args[1] if len(ctx.args) > 1 else "")
        if not approval_id:
            return SlashResult(ok=False, message="Usage: /leads reject <approval_id>")
        from keprix.crm.soft_wall import resolve_crm_approval

        row = resolve_crm_approval(ws, str(approval_id), status="rejected")
        if not row:
            return SlashResult(ok=False, message="Approval not found.")
        return SlashResult(ok=True, message=f"Rejected Soft Wall item {approval_id}.")

    if intent == "digest":
        from keprix.crm.funnel_analytics import build_digest

        digest = build_digest(ws, hours=24 if "week" not in str(parsed.get("period") or "") else 168)
        return SlashResult(ok=True, message=digest["message"], data=digest)

    if intent == "crm_ask":
        question = parsed.get("question") or ""
        if not question:
            return SlashResult(ok=False, message="Usage: /crm ask <question>")
        from keprix.crm.ask import ask_crm
        from keprix.crm.store import get_crm_store

        result = ask_crm(get_crm_store(), ws, question=question, limit=10)
        answer = result.get("answer") if isinstance(result, dict) else str(result)
        return SlashResult(ok=True, message=str(answer), data=result if isinstance(result, dict) else {})

    return SlashResult(ok=False, message="Unknown leads intent.")


async def handle_crm_command(ctx: SlashContext) -> SlashResult:
    denied = assert_channel_authz(ctx)
    if denied:
        return denied
    if ctx.args and str(ctx.args[0]).lower() == "ask":
        # Rewrite to leads handler path
        ctx.args = ["ask", *ctx.args[1:]]
        text = f"/crm ask {' '.join(ctx.args[1:])}"
        parsed = parse_leads_intent(text)
        if parsed:
            from keprix.crm.ask import ask_crm
            from keprix.crm.store import get_crm_store

            result = ask_crm(get_crm_store(), ctx.workspace_id, question=parsed.get("question"), limit=10)
            return SlashResult(ok=True, message=str(result.get("answer") or result), data=result)
    return await handle_leads_command(ctx)
