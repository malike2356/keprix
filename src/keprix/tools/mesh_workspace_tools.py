"""Agent tools for viCal, calendar list, and contacts (Telegram pilot mesh)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.tools.registry import registry

TOOLSET = "workspace_mesh"


def _check_vical() -> bool | str:
    if os.environ.get("KEPRIX_VICAL_ENABLED", "1").strip().lower() in {"0", "false", "no", "off"}:
        return "viCal disabled (KEPRIX_VICAL_ENABLED=0)"
    return True


def _uid(args: dict[str, Any], **kwargs: Any) -> str:
    for key in ("user_id", "username", "owner_id"):
        if args.get(key):
            return str(args[key])
        if kwargs.get(key):
            return str(kwargs[key])
    return str(os.environ.get("KEPRIX_MESH_USER_ID") or "default")


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = str(value).replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _handle_vical_slots(args: dict[str, Any], **kwargs: Any) -> str:
    from keprix.vical.seed import ensure_default_consultation
    from keprix.vical.slots import SlotEngine

    uid = _uid(args, **kwargs)
    ensure_default_consultation(uid)
    count = int(args.get("count") or 10)
    slug = str(args.get("slug") or "consultation")
    start = _parse_dt(args["start"]) if args.get("start") else None
    try:
        slots = SlotEngine().offer_slots(uid, slug=slug, start=start, count=count)
        return json.dumps({"items": [s.to_dict() for s in slots]})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def _handle_vical_create(args: dict[str, Any], **kwargs: Any) -> str:
    from keprix.vical.bookings import BookingLifecycle, BookingLifecycleError
    from keprix.vical.seed import ensure_default_consultation

    uid = _uid(args, **kwargs)
    ensure_default_consultation(uid)
    try:
        booking = BookingLifecycle().create(
            uid,
            slug=str(args.get("slug") or "consultation"),
            event_type_id=args.get("event_type_id"),
            guest_name=str(args.get("guest_name") or "").strip(),
            guest_email=str(args.get("guest_email") or "").strip(),
            starts_at=_parse_dt(args.get("starts_at")),
            ends_at=_parse_dt(args["ends_at"]) if args.get("ends_at") else None,
            source="agent",
            notes=args.get("notes"),
            contact_id=args.get("contact_id"),
            skip_slot_check=bool(args.get("skip_slot_check", False)),
        )
        return json.dumps(booking.to_dict())
    except (BookingLifecycleError, Exception) as exc:
        return json.dumps({"error": str(exc)})


def _handle_vical_list(args: dict[str, Any], **kwargs: Any) -> str:
    from keprix.vical.seed import ensure_default_consultation
    from keprix.vical.store import vical_store

    uid = _uid(args, **kwargs)
    ensure_default_consultation(uid)
    rows = vical_store.list_bookings(uid)
    limit = int(args.get("limit") or 20)
    return json.dumps({"items": [b.to_dict() for b in rows[:limit]]})


def _handle_vical_cancel(args: dict[str, Any], **kwargs: Any) -> str:
    from keprix.vical.bookings import BookingLifecycle, BookingLifecycleError

    uid = _uid(args, **kwargs)
    booking_id = str(args.get("booking_id") or "").strip()
    guest_token = str(args.get("guest_token") or "").strip()
    try:
        life = BookingLifecycle()
        if guest_token:
            booking = life.cancel_by_guest_token(guest_token, reason=args.get("reason"))
        else:
            booking = life.cancel(uid, booking_id, reason=args.get("reason"))
        return json.dumps(booking.to_dict())
    except (BookingLifecycleError, Exception) as exc:
        return json.dumps({"error": str(exc)})


def _handle_calendar_list(args: dict[str, Any], **kwargs: Any) -> str:
    from keprix.workspace.repository import workspace_repo

    uid = _uid(args, **kwargs)
    user = {"id": uid, "username": uid}
    start = _parse_dt(args["start"]) if args.get("start") else datetime.now(timezone.utc)
    end = _parse_dt(args["end"]) if args.get("end") else start + timedelta(days=7)

    def _ser(event: dict[str, Any]) -> dict[str, Any]:
        out = dict(event)
        for key in ("start_at", "end_at", "created_at", "updated_at"):
            if hasattr(out.get(key), "isoformat"):
                out[key] = out[key].isoformat()
        return out

    try:
        events = workspace_repo.list_events(user, start=start, end=end)
        return json.dumps({"items": [_ser(e) for e in events]})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def _run_async(coro: Any) -> Any:
    import asyncio
    import concurrent.futures

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _handle_contacts_search(args: dict[str, Any], **kwargs: Any) -> str:
    from keprix.contacts.search import contact_search

    uid = _uid(args, **kwargs)
    query = str(args.get("query") or "").strip()
    limit = int(args.get("limit") or 5)
    try:
        rows = _run_async(contact_search(query, limit=limit, user_id=uid))
        return json.dumps({"items": rows})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def _handle_contacts_get(args: dict[str, Any], **kwargs: Any) -> str:
    from keprix.contacts.search import contact_get

    contact_id = str(args.get("contact_id") or args.get("id") or "").strip()
    try:
        row = _run_async(contact_get(contact_id))
        return json.dumps(row or {"error": "not found"})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required or [],
        },
    }


registry.register(
    name="vical_offer_slots",
    toolset=TOOLSET,
    schema=_schema(
        "vical_offer_slots",
        "Offer available viCal booking slots for the host (default Consultation).",
        {
            "user_id": {"type": "string", "description": "Host user id (optional)"},
            "slug": {"type": "string", "description": "Event type slug (default consultation)"},
            "start": {"type": "string", "description": "ISO start search window"},
            "count": {"type": "integer", "description": "Max slots"},
        },
    ),
    handler=_handle_vical_slots,
    check_fn=_check_vical,
)

registry.register(
    name="vical_create_booking",
    toolset=TOOLSET,
    schema=_schema(
        "vical_create_booking",
        "Create a viCal booking for a guest at starts_at. Link contact_id when known.",
        {
            "guest_name": {"type": "string"},
            "guest_email": {"type": "string"},
            "starts_at": {"type": "string", "description": "ISO datetime"},
            "ends_at": {"type": "string"},
            "slug": {"type": "string"},
            "contact_id": {"type": "string"},
            "notes": {"type": "string"},
            "user_id": {"type": "string"},
        },
        required=["guest_name", "guest_email", "starts_at"],
    ),
    handler=_handle_vical_create,
    check_fn=_check_vical,
)

registry.register(
    name="vical_list_bookings",
    toolset=TOOLSET,
    schema=_schema(
        "vical_list_bookings",
        "List viCal bookings for the host.",
        {"user_id": {"type": "string"}, "limit": {"type": "integer"}},
    ),
    handler=_handle_vical_list,
    check_fn=_check_vical,
)

registry.register(
    name="vical_cancel_booking",
    toolset=TOOLSET,
    schema=_schema(
        "vical_cancel_booking",
        "Cancel a viCal booking by booking_id or guest_token.",
        {
            "booking_id": {"type": "string"},
            "guest_token": {"type": "string"},
            "reason": {"type": "string"},
            "user_id": {"type": "string"},
        },
    ),
    handler=_handle_vical_cancel,
    check_fn=_check_vical,
)

registry.register(
    name="calendar_list_events",
    toolset=TOOLSET,
    schema=_schema(
        "calendar_list_events",
        "List workspace calendar events in a time range (default next 7 days).",
        {
            "user_id": {"type": "string"},
            "start": {"type": "string"},
            "end": {"type": "string"},
        },
    ),
    handler=_handle_calendar_list,
)

registry.register(
    name="contacts_search",
    toolset=TOOLSET,
    schema=_schema(
        "contacts_search",
        "Search workspace contacts by name, email, or phone fragment.",
        {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
            "user_id": {"type": "string"},
        },
        required=["query"],
    ),
    handler=_handle_contacts_search,
)

registry.register(
    name="contacts_get",
    toolset=TOOLSET,
    schema=_schema(
        "contacts_get",
        "Get a contact by id.",
        {"contact_id": {"type": "string"}, "id": {"type": "string"}},
        required=[],
    ),
    handler=_handle_contacts_get,
)

PILOT_TOOL_NAMES = (
    "vical_offer_slots",
    "vical_create_booking",
    "vical_list_bookings",
    "vical_cancel_booking",
    "calendar_list_events",
    "contacts_search",
    "contacts_get",
    "create_lead",
    "list_leads",
    "link_booking_to_lead",
)

# Side-effect imports so domain pack + lead tools register with the mesh suite.
try:
    import keprix.tools.product_lead_tools  # noqa: F401
except Exception:
    pass
try:
    import keprix.tools.domain_pack_tools  # noqa: F401
except Exception:
    pass

