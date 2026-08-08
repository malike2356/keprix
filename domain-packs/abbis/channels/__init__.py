"""Channel adapters and confirmation gates for ABBIS field workflows."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from typing import Any

_LOCK = threading.RLock()
_SEEN_DELIVERIES: set[str] = set()

WRITE_INTENTS = frozenset(
    {
        "financial",
        "inventory",
        "worker",
        "customer",
        "compliance",
        "marketplace",
    }
)

NUMBER_UNIT_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>m|metres?|meters?|lpm|ghs|pipes?|rods?|bags?)",
    re.I,
)


def reset_channel_state() -> None:
    with _LOCK:
        _SEEN_DELIVERIES.clear()


def resolve_linked_identity(channel: str, external_id: str, links: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    key = f"{channel}:{external_id}"
    return links.get(key)


def confirm_numbers_and_units(text: str) -> dict[str, Any]:
    matches = [
        {"raw": m.group(0), "number": m.group("num"), "unit": m.group("unit").lower()}
        for m in NUMBER_UNIT_RE.finditer(text or "")
    ]
    return {
        "requires_confirmation": bool(matches),
        "items": matches,
        "prompt": "Please confirm each number and unit before I write anything.",
    }


def confirmation_gate(*, intent: str, spoken_or_typed: str, confirmed: bool) -> dict[str, Any]:
    numbers = confirm_numbers_and_units(spoken_or_typed)
    if intent in WRITE_INTENTS:
        if numbers["requires_confirmation"] and not confirmed:
            return {
                "allowed": False,
                "reason": "numbers_units_unconfirmed",
                "confirmation": numbers,
            }
        if not confirmed:
            return {
                "allowed": False,
                "reason": "structured_confirmation_required",
                "confirmation": {
                    "requires_confirmation": True,
                    "prompt": f"Confirm {intent} write before apply.",
                },
            }
    return {"allowed": True, "confirmation": numbers}


def ingest_channel_message(
    *,
    channel: str,
    delivery_id: str,
    external_id: str,
    text: str,
    links: dict[str, dict[str, Any]],
    intent: str = "read",
    confirmed: bool = False,
) -> dict[str, Any]:
    with _LOCK:
        if delivery_id in _SEEN_DELIVERIES:
            return {"status": "deduped", "delivery_id": delivery_id, "channel": channel}
        _SEEN_DELIVERIES.add(delivery_id)

    identity = resolve_linked_identity(channel, external_id, links)
    if not identity:
        return {"status": "unlinked", "channel": channel, "error": "link_identity_first"}

    if channel in {"whatsapp", "telegram"} and identity.get("chat_type") == "group":
        if intent in WRITE_INTENTS or any(k in (text or "").lower() for k in ("pay", "ghs", "wage", "stock")):
            return {
                "status": "denied",
                "reason": "sensitive_data_blocked_in_group",
                "channel": channel,
            }

    gate = confirmation_gate(intent=intent, spoken_or_typed=text, confirmed=confirmed)
    if not gate["allowed"]:
        return {"status": "needs_confirmation", "channel": channel, **gate, "identity": identity}

    digest = hashlib.sha256(f"{channel}:{delivery_id}:{text}".encode()).hexdigest()[:16]
    return {
        "status": "accepted",
        "channel": channel,
        "delivery_id": delivery_id,
        "identity": identity,
        "message_hash": digest,
        "resume_boundary": "confirmation",
    }


def voice_workflow_contract(workflow_id: str) -> dict[str, Any]:
    workflows = {
        "vw1": {"name": "submit_drilling_log", "channel_default": "whatsapp", "write": True},
        "vw2": {"name": "price_quote", "channel_default": "whatsapp", "write": True},
        "vw3": {"name": "record_wages", "channel_default": "whatsapp", "write": True},
        "vw4": {"name": "report_problem", "channel_default": "whatsapp", "write": False},
        "vw5": {"name": "client_project_status", "channel_default": "telegram", "write": False},
        "vw6": {"name": "association_dues", "channel_default": "web", "write": True},
        "vw7": {"name": "association_broadcast", "channel_default": "web", "write": True},
    }
    row = workflows.get(workflow_id)
    if not row:
        raise KeyError(workflow_id)
    return {"workflow_id": workflow_id, **row, "requires_product_context": True}


def rag_retrieve(
    *,
    query: str,
    tenant_id: str,
    accessory: str,
    corpora: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Retrieval favouring law/standards, product specs, tenant policy, verified records."""
    order = {"law": 0, "standard": 1, "product_spec": 2, "tenant_policy": 3, "verified_record": 4, "general": 5}
    hits = []
    for doc in corpora:
        if doc.get("tenant_id") not in {None, "", "public", "association", tenant_id}:
            continue
        if doc.get("accessory") and doc.get("accessory") != accessory and doc.get("scope") != "public":
            continue
        if query.lower() in json.dumps(doc).lower() or not query:
            hits.append(doc)
    hits.sort(key=lambda d: order.get(str(d.get("authority") or "general"), 9))
    return [
        {
            "id": h.get("id"),
            "citation": h.get("citation"),
            "uncertainty": h.get("uncertainty", "medium"),
            "scope": h.get("scope"),
            "authority": h.get("authority"),
        }
        for h in hits
    ]
