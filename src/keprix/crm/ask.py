"""Deterministic CRM ask-data: filter/SQL-style counts with cited record ids."""

from __future__ import annotations

import re
from typing import Any

from keprix.crm.models import CrmStage
from keprix.crm.store import CrmStore

_ENTITY_ALIASES = {
    "lead": "leads",
    "leads": "leads",
    "contact": "contacts",
    "contacts": "contacts",
    "account": "accounts",
    "accounts": "accounts",
    "deal": "deals",
    "deals": "deals",
    "list": "lists",
    "lists": "lists",
}

_OPEN_STAGES = frozenset(
    {
        CrmStage.DISCOVERED,
        CrmStage.ENRICHED,
        CrmStage.LISTED,
        CrmStage.APPROVED,
        CrmStage.ENROLLED,
        CrmStage.CONTACTED,
        CrmStage.ENGAGED,
        CrmStage.QUALIFIED,
        CrmStage.BOOKED,
    }
)


def format_telegram_reply(text: str, *, max_len: int = 3500) -> str:
    """Telegram-safe short reply: plain text, hard capped length."""
    cleaned = str(text or "").replace("\r\n", "\n").strip()
    cleaned = re.sub(r"[*_`~|]{2,}", "", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if len(cleaned) <= max_len:
        return cleaned
    suffix = "\n...[truncated]"
    keep = max(0, max_len - len(suffix))
    return cleaned[:keep].rstrip() + suffix


def filter_rows(
    rows: list[dict[str, Any]],
    *,
    q: str | None = None,
    stage: str | None = None,
    stages: list[str] | None = None,
    source: str | None = None,
    domain_pack: str | None = None,
    tag: str | None = None,
    open_only: bool = False,
) -> list[dict[str, Any]]:
    out = rows
    if open_only:
        out = [r for r in out if str(r.get("stage") or "") in _OPEN_STAGES]
    if stage:
        out = [r for r in out if str(r.get("stage") or "") == stage]
    if stages:
        wanted = {str(s) for s in stages}
        out = [r for r in out if str(r.get("stage") or "") in wanted]
    if source:
        out = [r for r in out if str(r.get("source") or "") == source]
    if domain_pack:
        out = [r for r in out if str(r.get("domain_pack") or "") == domain_pack]
    if tag:
        out = [r for r in out if tag in (r.get("tags") or [])]
    if q:
        needle = q.lower()
        filtered: list[dict[str, Any]] = []
        for r in out:
            blob = " ".join(
                str(r.get(k) or "")
                for k in ("name", "display_name", "company_name", "company_number", "domain")
            ).lower()
            emails = r.get("emails") or []
            email_blob = " ".join(
                str(e.get("address") if isinstance(e, dict) else e) for e in emails
            ).lower()
            tags = " ".join(str(t) for t in (r.get("tags") or [])).lower()
            if needle in blob or needle in email_blob or needle in tags:
                filtered.append(r)
        out = filtered
    return out


def _list_entity(store: CrmStore, workspace_id: str, entity: str) -> list[dict[str, Any]]:
    if entity == "leads":
        return store.list_leads(workspace_id, limit=5000)
    if entity == "contacts":
        return store.list_contacts(workspace_id, limit=5000)
    if entity == "accounts":
        return store.list_accounts(workspace_id, limit=5000)
    if entity == "deals":
        return store.list_deals(workspace_id, limit=5000)
    if entity == "lists":
        return store.list_lists(workspace_id, limit=5000)
    return []


def parse_ask_filters(
    question: str | None = None,
    *,
    entity: str | None = None,
    stage: str | None = None,
    domain_pack: str | None = None,
    tag: str | None = None,
    source: str | None = None,
    q: str | None = None,
    open_only: bool | None = None,
) -> dict[str, Any]:
    """Map structured args + light NL heuristics to filter dict. Never invent rows."""
    text = str(question or "").strip().lower()
    resolved_entity = _ENTITY_ALIASES.get(str(entity or "").strip().lower(), "")
    if not resolved_entity and text:
        for key, value in _ENTITY_ALIASES.items():
            if re.search(rf"\b{re.escape(key)}\b", text):
                resolved_entity = value
                break
    if not resolved_entity:
        resolved_entity = "leads"

    resolved_stage = stage
    resolved_open = bool(open_only) if open_only is not None else False
    if not resolved_stage and text:
        if re.search(r"\bopen\b", text):
            resolved_open = True
        for st in (
            CrmStage.CUSTOMER,
            CrmStage.PAYING,
            CrmStage.QUALIFIED,
            CrmStage.BOOKED,
            CrmStage.LISTED,
            CrmStage.ENROLLED,
            CrmStage.CONTACTED,
            CrmStage.DISCOVERED,
            CrmStage.SUPPRESSED,
        ):
            if re.search(rf"\b{re.escape(st)}\b", text):
                resolved_stage = st
                break

    resolved_pack = domain_pack
    resolved_tag = tag
    if text:
        m = re.search(r"\b(?:icp|pack|domain[_\s-]?pack)\s*[:=]?\s*([a-z0-9_-]+)", text)
        if m and not resolved_pack:
            resolved_pack = m.group(1)
        m2 = re.search(r"\bin\s+([a-z0-9_-]+)\s+icp\b", text)
        if m2 and not resolved_pack and not resolved_tag:
            resolved_tag = m2.group(1)
            resolved_pack = m2.group(1)
        m3 = re.search(r"\btag\s*[:=]?\s*([a-z0-9_-]+)", text)
        if m3 and not resolved_tag:
            resolved_tag = m3.group(1)

    resolved_q = q
    if not resolved_q and text:
        # Keep leftover content only when it looks like a search fragment, not full NL.
        if len(text.split()) <= 4 and not text.startswith("how many"):
            resolved_q = text

    return {
        "entity": resolved_entity,
        "stage": resolved_stage,
        "domain_pack": resolved_pack,
        "tag": resolved_tag,
        "source": source,
        "q": resolved_q,
        "open_only": resolved_open,
    }


def ask_crm(
    store: CrmStore,
    workspace_id: str,
    *,
    question: str | None = None,
    entity: str | None = None,
    stage: str | None = None,
    domain_pack: str | None = None,
    tag: str | None = None,
    source: str | None = None,
    q: str | None = None,
    open_only: bool | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """Answer from real CRM rows only. Citations always include record ids."""
    ws = str(workspace_id or "").strip()
    if not ws:
        raise ValueError("workspace_id is required")

    filters = parse_ask_filters(
        question,
        entity=entity,
        stage=stage,
        domain_pack=domain_pack,
        tag=tag,
        source=source,
        q=q,
        open_only=open_only,
    )
    rows = _list_entity(store, ws, filters["entity"])
    matched = filter_rows(
        rows,
        q=filters.get("q"),
        stage=filters.get("stage"),
        source=filters.get("source"),
        domain_pack=filters.get("domain_pack"),
        tag=filters.get("tag"),
        open_only=bool(filters.get("open_only")),
    )
    limit = max(1, min(int(limit or 25), 100))
    sample = matched[:limit]
    citations = [
        {
            "entity_type": filters["entity"][:-1] if filters["entity"].endswith("s") else filters["entity"],
            "id": r["id"],
            "name": r.get("name") or r.get("display_name") or r.get("company_name"),
            "stage": r.get("stage"),
        }
        for r in sample
        if r.get("id")
    ]
    answer = f"{len(matched)} {filters['entity']} match the filter"
    if filters.get("stage"):
        answer += f" (stage={filters['stage']})"
    if filters.get("open_only"):
        answer += " (open stages)"
    if filters.get("domain_pack"):
        answer += f" (domain_pack={filters['domain_pack']})"
    if filters.get("tag"):
        answer += f" (tag={filters['tag']})"
    answer += "."
    if citations:
        ids = ", ".join(c["id"] for c in citations[:10])
        answer += f" Cited ids: {ids}."
        if len(matched) > len(citations):
            answer += f" Showing {len(citations)} of {len(matched)}."

    return {
        "ok": True,
        "workspace_id": ws,
        "question": question,
        "filters": filters,
        "count": len(matched),
        "citations": citations,
        "items": sample,
        "answer": answer,
        "telegram_reply": format_telegram_reply(answer),
        "invented": False,
    }
