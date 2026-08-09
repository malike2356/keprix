"""Telegram / channel funnel intents for CRM Soft Wall (prompts 446 + 627)."""

from __future__ import annotations

import base64
import re
from typing import Any

from keprix.slash.schemas import SlashContext, SlashResult

# Linked workspace authz: deny strangers (no workspace match / anonymous)
def assert_channel_authz(ctx: SlashContext) -> SlashResult | None:
    user = str(ctx.user_id or "").strip()
    if not user or user in {"anonymous", "stranger", "unknown"}:
        return SlashResult(ok=False, message="Denied: link your Telegram account to a Keprix workspace user first.")
    if not str(ctx.workspace_id or "").strip():
        return SlashResult(ok=False, message="Denied: no workspace bound to this chat.")
    return None


def parse_leads_intent(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    lower = raw.lower()
    m = re.search(r"find\s+(.+?)\s+in\s+([a-zA-Z\s]+)$", lower)
    if m:
        return {"intent": "find", "query": m.group(1).strip(), "location": m.group(2).strip()}
    if lower.startswith("/leads") or lower.startswith("leads "):
        parts = raw.split()
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
            if sub == "digest_outcomes":
                return {"intent": "digest_outcomes", "period": rest or "daily"}
            if sub == "reject":
                return {"intent": "reject", "approval_id": rest or None}
            if sub == "import_sheet":
                return {"intent": "import_sheet", "args": rest}
            if sub == "enrich":
                return {"intent": "enrich", "args": rest}
            if sub == "add_to_list":
                return {"intent": "add_to_list", "list_name": rest or None}
            if sub == "draft_campaign":
                return {"intent": "draft_campaign", "args": rest}
            if sub == "journey":
                return {"intent": "journey", "args": rest}
    if lower.startswith("/crm") or lower.startswith("crm "):
        parts = raw.split(maxsplit=2)
        sub = parts[1].lower() if len(parts) > 1 else ""
        rest = parts[2] if len(parts) > 2 else ""
        if sub == "ask":
            return {"intent": "crm_ask", "question": rest}
    return None


def _usage() -> str:
    return (
        "Usage: /leads find <query> [in place] | approve <id> | reject <id> | digest | "
        "import_sheet | enrich | add_to_list [name] | draft_campaign | digest_outcomes | "
        "/crm ask <question>"
    )


async def handle_leads_command(ctx: SlashContext) -> SlashResult:
    denied = assert_channel_authz(ctx)
    if denied:
        return denied

    text = ctx.raw_text or f"/{ctx.command} {' '.join(ctx.args)}"
    parsed = parse_leads_intent(text)
    if not parsed and ctx.args:
        sub = str(ctx.args[0]).lower()
        rest = " ".join(ctx.args[1:])
        parsed = parse_leads_intent(f"/leads {sub} {rest}")
    if not parsed:
        return SlashResult(ok=False, message=_usage())

    ws = ctx.workspace_id
    intent = parsed["intent"]

    if intent == "find":
        if ctx.role not in {"operator", "admin", "owner", "user"} and ctx.role == "viewer":
            return SlashResult(ok=False, message="Denied: operator role required to start discovery.")
        query = parsed.get("query") or ""
        location = parsed.get("location")
        try:
            from keprix.crm.store import get_crm_store

            store = get_crm_store()
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
        # Continue channel journey enroll when approval was a campaign draft
        kind = str(row.get("approval_kind") or "")
        if kind == "channel_journey_campaign":
            try:
                from keprix.crm.channel_journey import run_channel_journey
                import json

                payload = row.get("payload") or {}
                if isinstance(row.get("payload_json"), str):
                    try:
                        payload = json.loads(row["payload_json"])
                    except json.JSONDecodeError:
                        payload = {}
                journey = run_channel_journey(
                    ws,
                    channel="telegram",
                    list_id=payload.get("list_id"),
                    sequence_id=payload.get("sequence_id"),
                    campaign_name=None,
                    approve_enroll=True,
                    approval_id=str(approval_id),
                    actor_id=ctx.user_id,
                )
                return SlashResult(
                    ok=True,
                    message=f"Approved Soft Wall {approval_id}; journey enroll status={journey.get('status')}.",
                    data={"approval": row, "journey": journey},
                )
            except Exception as exc:
                return SlashResult(
                    ok=True,
                    message=f"Approved {approval_id}; enroll follow-up note: {exc}",
                    data={"approval": row},
                )
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

    if intent in {"digest", "digest_outcomes"}:
        from keprix.crm.funnel_analytics import build_digest, extended_funnel_report

        digest = build_digest(ws, hours=24 if "week" not in str(parsed.get("period") or "") else 168)
        if intent == "digest_outcomes":
            report = extended_funnel_report(ws)
            digest["conversion_rates"] = report.get("conversion_rates")
            digest["outcome_rollups"] = report.get("outcome_rollups")
            digest["message"] = digest["message"] + " Outcomes attached."
        return SlashResult(ok=True, message=digest["message"], data=digest)

    if intent in {"import_sheet", "enrich", "add_to_list", "draft_campaign", "journey"}:
        if ctx.role in {"viewer"}:
            return SlashResult(ok=False, message="Denied: journey intents require operator.")
        # Attachment bytes may arrive as base64 in ctx.attachments / data
        payload: bytes | None = None
        filename = "channel-upload.csv"
        attachments = getattr(ctx, "attachments", None) or []
        if isinstance(attachments, list) and attachments:
            att = attachments[0]
            if isinstance(att, dict):
                filename = str(att.get("filename") or filename)
                raw = att.get("content") or att.get("bytes")
                if isinstance(raw, (bytes, bytearray)):
                    payload = bytes(raw)
                elif isinstance(raw, str):
                    try:
                        payload = base64.b64decode(raw)
                    except Exception:
                        payload = raw.encode("utf-8")
        from keprix.crm.channel_journey import run_channel_journey, journey_status

        if intent == "add_to_list" and not payload:
            # Status-only list helper
            status = journey_status(ws)
            return SlashResult(
                ok=True,
                message=f"Journey status: {len(status.get('pending_approvals') or [])} pending Soft Wall.",
                data=status,
            )
        if not payload and intent != "journey":
            return SlashResult(
                ok=False,
                message=(
                    f"Attach a CSV/XLSX spreadsheet then run /leads {intent}. "
                    "Without bytes, only journey status is available via /leads journey."
                ),
            )
        if intent == "journey" and not payload:
            status = journey_status(ws)
            return SlashResult(ok=True, message="Channel journey status loaded.", data=status)

        result = run_channel_journey(
            ws,
            payload=payload,
            filename=filename,
            channel="telegram",
            list_name=parsed.get("list_name") if intent == "add_to_list" else None,
            skip_enrich=(intent == "import_sheet"),
            actor_id=ctx.user_id,
        )
        return SlashResult(
            ok=True,
            message=(
                f"Channel journey {result.get('status')}: list={result.get('list_id')} "
                f"campaign={result.get('campaign_id')}. Soft Wall approvals at /crm."
            ),
            data=result,
        )

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
        ctx.args = ["ask", *ctx.args[1:]]
        text = f"/crm ask {' '.join(ctx.args[1:])}"
        parsed = parse_leads_intent(text)
        if parsed:
            from keprix.crm.ask import ask_crm
            from keprix.crm.store import get_crm_store

            result = ask_crm(get_crm_store(), ctx.workspace_id, question=parsed.get("question"), limit=10)
            return SlashResult(ok=True, message=str(result.get("answer") or result), data=result)
    return await handle_leads_command(ctx)
