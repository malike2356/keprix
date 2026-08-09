"""HTTP routes for Keprix viCal (authenticated host + public guest)."""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.vical.bookings import BookingLifecycle, BookingLifecycleError
from keprix.vical.conferencing import sync_notes, to_public_booking_view
from keprix.vical.saga import book_with_saga
from keprix.vical.calendar.calendar_webhooks import handle_google_calendar_webhook
from keprix.vical.calendar.delivery_state import booking_invitation_view
from keprix.vical.calendar.projection_store import get_projection_store
from keprix.vical.calendar.sync_booking import renew_expiring_watches
from keprix.vical.zoom_webhooks import handle_zoom_webhook
from keprix.vical.deposits import DepositError, create_checkout_session, mark_deposit_paid
from keprix.vical.ics import booking_ics_dict, render_booking_ics
from keprix.vical.intake import IntakeDisqualified, IntakeError, intake_required_for_source, validate_intake_answers
from keprix.vical.reminders import process_reminders
from keprix.vical.seed import ensure_default_consultation
from keprix.vical.slots import SlotEngine
from keprix.vical.store import IsolationError, vical_store

router = APIRouter(prefix="/api/vical", tags=["vical"])


def _uid(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


def _enabled() -> bool:
    return os.environ.get("KEPRIX_VICAL_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}


def _resolve_public_host(public_slug: str) -> dict[str, Any]:
    profile = vical_store.resolve_host_by_slug(public_slug)
    if profile is None:
        # Fallback: treat slug as user_id for seeded hosts
        profile = vical_store.get_host_profile(public_slug)
        if profile is None and vical_store.list_event_types(public_slug):
            profile = {"user_id": public_slug, "public_slug": public_slug, "display_name": public_slug}
            vical_store.upsert_host_profile(public_slug, public_slug=public_slug, display_name=public_slug)
            profile = vical_store.get_host_profile(public_slug)
    if profile is None:
        raise HTTPException(status_code=404, detail="host not found")
    return profile


class EventTypeCreate(BaseModel):
    slug: str
    name: str
    duration_minutes: int = 30
    buffer_before_minutes: int = 0
    buffer_after_minutes: int = 0
    min_notice_minutes: int = 120
    horizon_days: int = 30
    location_mode: str = "unspecified"
    requires_approval: bool = False
    requires_deposit: bool = False
    deposit_minor: int | None = None
    deposit_currency: str | None = None
    intake_pool_id: str | None = None
    active: bool = True


class EventTypePatch(BaseModel):
    name: str | None = None
    duration_minutes: int | None = None
    requires_approval: bool | None = None
    requires_deposit: bool | None = None
    deposit_minor: int | None = None
    deposit_currency: str | None = None
    intake_pool_id: str | None = None
    active: bool | None = None
    location_mode: str | None = None


class AvailabilityCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: str
    end_time: str
    timezone: str = "UTC"
    event_type_id: str | None = None


class BlackoutCreate(BaseModel):
    starts_on: date
    ends_on: date
    reason: str | None = None


class BookingCreate(BaseModel):
    guest_name: str
    guest_email: str
    starts_at: datetime
    ends_at: datetime | None = None
    event_type_id: str | None = None
    slug: str | None = "consultation"
    notes: str | None = None
    meeting_url: str | None = None
    intake_answers: dict[str, Any] | None = None
    source: Literal["public", "api", "agent", "echo", "voice"] = "api"
    holder_token: str | None = None
    lock_id: str | None = None
    # Host calendar / inbox create may pick a free grid slot outside public offer windows.
    skip_slot_check: bool = False


class BookingReschedule(BaseModel):
    starts_at: datetime
    ends_at: datetime | None = None


class HostProfileUpdate(BaseModel):
    public_slug: str | None = None
    display_name: str | None = None
    webhook_url: str | None = None
    webhook_secret: str | None = None
    meeting_url_template: str | None = None


class IntakePoolCreate(BaseModel):
    name: str
    questions: list[dict[str, Any]] = Field(default_factory=list)


class PublicBookingCreate(BaseModel):
    event_type_slug: str | None = "consultation"
    event_type_id: str | None = None
    guest_name: str
    guest_email: str
    starts_at: datetime
    ends_at: datetime | None = None
    notes: str | None = None
    intake_answers: dict[str, Any] | None = None
    holder_token: str | None = None
    lock_id: str | None = None


class PublicReschedule(BaseModel):
    guest_token: str
    starts_at: datetime
    ends_at: datetime | None = None


class PublicCancel(BaseModel):
    guest_token: str
    reason: str | None = None


class IntakeValidateBody(BaseModel):
    event_type_slug: str | None = "consultation"
    event_type_id: str | None = None
    answers: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Host (authenticated)
# ---------------------------------------------------------------------------


@router.get("/status")
async def status(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    uid = _uid(user)
    ensure_default_consultation(uid)
    types = vical_store.list_event_types(uid, active_only=True)
    profile = vical_store.get_host_profile(uid) or {}
    return {
        "ok": True,
        "enabled": _enabled(),
        "event_type_count": len(types),
        "default_slug": "consultation",
        "public_slug": profile.get("public_slug"),
        "public_book_path": f"/book/{profile.get('public_slug') or uid}",
        "sync": sync_notes(),
        "docs": "/docs/features/vical.md",
    }


@router.post("/seed")
async def seed_defaults(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    result = ensure_default_consultation(_uid(user))
    return {
        "ok": True,
        "created_event_type": result["created_event_type"],
        "created_rules": result["created_rules"],
        "event_type": result["event_type"].to_dict(),
        "host_profile": result.get("host_profile"),
    }


@router.get("/host-profile")
async def get_host_profile(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    uid = _uid(user)
    ensure_default_consultation(uid)
    profile = vical_store.get_host_profile(uid) or {}
    return {"profile": profile, "public_book_path": f"/book/{profile.get('public_slug') or uid}"}


@router.put("/host-profile")
async def put_host_profile(body: HostProfileUpdate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        profile = vical_store.upsert_host_profile(_uid(user), **body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"profile": profile, "public_book_path": f"/book/{profile.get('public_slug')}"}


@router.get("/event-types")
async def list_event_types(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    rows = vical_store.list_event_types(_uid(user))
    return {"items": [r.to_dict() for r in rows]}


@router.post("/event-types", status_code=201)
async def create_event_type(body: EventTypeCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        et = vical_store.create_event_type(user_id=_uid(user), **body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return et.to_dict()


@router.patch("/event-types/{event_type_id}")
async def patch_event_type(
    event_type_id: str,
    body: EventTypePatch,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        et = vical_store.update_event_type(_uid(user), event_type_id, **body.model_dump(exclude_none=True))
    except (ValueError, IsolationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return et.to_dict()


@router.get("/availability-rules")
async def list_availability(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    rows = vical_store.list_availability_rules(_uid(user))
    return {"items": [r.to_dict() for r in rows]}


@router.post("/availability-rules", status_code=201)
async def create_availability(body: AvailabilityCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        rule = vical_store.create_availability_rule(user_id=_uid(user), **body.model_dump())
    except (ValueError, IsolationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return rule.to_dict()


@router.get("/blackouts")
async def list_blackouts(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    rows = vical_store.list_blackouts(_uid(user))
    return {"items": [r.to_dict() for r in rows]}


@router.post("/blackouts", status_code=201)
async def create_blackout(body: BlackoutCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        bo = vical_store.create_blackout(user_id=_uid(user), **body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return bo.to_dict()


@router.get("/intake-pools")
async def list_intake_pools(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"items": vical_store.list_intake_pools(_uid(user))}


@router.post("/intake-pools", status_code=201)
async def create_intake_pool(body: IntakePoolCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return vical_store.create_intake_pool(user_id=_uid(user), name=body.name, questions=body.questions)


@router.get("/slots")
async def offer_slots(
    user: dict = Depends(get_current_user),
    event_type_id: str | None = None,
    slug: str | None = "consultation",
    start: datetime | None = None,
    count: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    engine = SlotEngine()
    try:
        slots = engine.offer_slots(
            _uid(user),
            event_type_id=event_type_id,
            slug=slug,
            start=start,
            count=count,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": [s.to_dict() for s in slots]}


@router.get("/bookings")
async def list_bookings(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    rows = vical_store.list_bookings(_uid(user))
    return {"items": [r.to_dict() for r in rows]}


@router.get("/bookings/{booking_id}")
async def get_booking(booking_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return vical_store.get_booking(_uid(user), booking_id).to_dict()
    except IsolationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/bookings", status_code=201)
async def create_booking(body: BookingCreate, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    uid = _uid(user)
    try:
        et = SlotEngine().resolve_event_type(uid, event_type_id=body.event_type_id, slug=body.slug)
        if et.intake_pool_id and intake_required_for_source(body.source):
            pool = vical_store.get_intake_pool(uid, et.intake_pool_id)
            cleaned = validate_intake_answers(pool, body.intake_answers)
            body = body.model_copy(update={"intake_answers": cleaned})
        result = book_with_saga(
            uid,
            event_type_id=body.event_type_id,
            slug=body.slug,
            guest_name=body.guest_name,
            guest_email=body.guest_email,
            starts_at=body.starts_at,
            ends_at=body.ends_at,
            source=body.source,
            notes=body.notes,
            meeting_url=body.meeting_url,
            intake_answers=body.intake_answers,
            holder_token=body.holder_token,
            lock_id=body.lock_id,
            skip_slot_check=body.skip_slot_check,
            workspace_id=uid,
            prefer_managed_zoom=True,
        )
    except IntakeDisqualified as exc:
        raise HTTPException(status_code=422, detail={"code": "intake_disqualified", "message": str(exc)}) from exc
    except IntakeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BookingLifecycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    booking = result["booking"]
    payload = to_public_booking_view(booking.to_dict())
    payload["duplicate"] = result.get("duplicate")
    payload["conferenceManaged"] = result.get("conferenceManaged")
    payload["actionRequired"] = result.get("actionRequired")
    return payload


@router.post("/bookings/{booking_id}/approve")
async def approve_booking(booking_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return BookingLifecycle().approve(_uid(user), booking_id).to_dict()
    except (BookingLifecycleError, IsolationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bookings/{booking_id}/reject")
async def reject_booking(booking_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return BookingLifecycle().reject(_uid(user), booking_id).to_dict()
    except (BookingLifecycleError, IsolationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return BookingLifecycle().cancel(_uid(user), booking_id).to_dict()
    except (BookingLifecycleError, IsolationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bookings/{booking_id}/reschedule")
async def reschedule_booking(
    booking_id: str,
    body: BookingReschedule,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return (
            BookingLifecycle()
            .reschedule(_uid(user), booking_id, starts_at=body.starts_at, ends_at=body.ends_at)
            .to_dict()
        )
    except (BookingLifecycleError, IsolationError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/bookings/{booking_id}/ics")
async def booking_ics(booking_id: str, user: dict = Depends(get_current_user)) -> Response:
    try:
        booking = vical_store.get_booking(_uid(user), booking_id)
        et = vical_store.get_event_type(_uid(user), booking.event_type_id)
    except IsolationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    body = render_booking_ics(booking, title=f"{et.name}: {booking.guest_name}")
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="vical-{booking.id}.ics"'},
    )


@router.post("/reminders/run")
async def run_reminders(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return process_reminders()


@router.post("/deposits/{booking_id}/checkout")
async def deposit_checkout(booking_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return create_checkout_session(_uid(user), booking_id)
    except (DepositError, IsolationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/deposits/mark-paid")
async def deposit_mark_paid(
    user: dict = Depends(get_current_user),
    booking_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    try:
        booking = mark_deposit_paid(booking_id=booking_id, session_id=session_id, user_id=_uid(user))
    except (DepositError, IsolationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return booking.to_dict()


# ---------------------------------------------------------------------------
# Public (unauthenticated)
# ---------------------------------------------------------------------------


@router.get("/public/hosts/{public_slug}")
async def public_host(public_slug: str) -> dict[str, Any]:
    profile = _resolve_public_host(public_slug)
    uid = str(profile["user_id"])
    ensure_default_consultation(uid)
    types = [et.to_dict() for et in vical_store.list_event_types(uid, active_only=True)]
    return {
        "host": {
            "public_slug": profile.get("public_slug"),
            "display_name": profile.get("display_name") or uid,
            "user_id": uid,
        },
        "event_types": types,
    }


@router.get("/public/hosts/{public_slug}/slots")
async def public_slots(
    public_slug: str,
    event_type_id: str | None = None,
    slug: str | None = "consultation",
    start: datetime | None = None,
    count: int = Query(20, ge=1, le=100),
) -> dict[str, Any]:
    profile = _resolve_public_host(public_slug)
    uid = str(profile["user_id"])
    try:
        slots = SlotEngine().offer_slots(uid, event_type_id=event_type_id, slug=slug, start=start, count=count)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": [s.to_dict() for s in slots]}


@router.get("/public/hosts/{public_slug}/intake")
async def public_intake(
    public_slug: str,
    event_type_id: str | None = None,
    slug: str | None = "consultation",
) -> dict[str, Any]:
    profile = _resolve_public_host(public_slug)
    uid = str(profile["user_id"])
    try:
        et = SlotEngine().resolve_event_type(uid, event_type_id=event_type_id, slug=slug)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not et.intake_pool_id:
        return {"required": False, "pool": None}
    try:
        pool = vical_store.get_intake_pool(uid, et.intake_pool_id)
    except IsolationError:
        return {"required": False, "pool": None}
    # Hide operator-only fields lightly
    safe = {
        "id": pool["id"],
        "name": pool.get("name"),
        "questions": [
            {
                "id": q.get("id"),
                "label": q.get("label") or q.get("id"),
                "type": q.get("type") or "text",
                "required": bool(q.get("required", True)),
                "options": q.get("options") or [],
            }
            for q in (pool.get("questions") or [])
        ],
    }
    return {"required": True, "pool": safe, "event_type_id": et.id}


@router.post("/public/hosts/{public_slug}/intake/validate")
async def public_intake_validate(public_slug: str, body: IntakeValidateBody) -> dict[str, Any]:
    profile = _resolve_public_host(public_slug)
    uid = str(profile["user_id"])
    try:
        et = SlotEngine().resolve_event_type(uid, event_type_id=body.event_type_id, slug=body.event_type_slug)
        if not et.intake_pool_id:
            return {"ok": True, "required": False, "answers": {}}
        pool = vical_store.get_intake_pool(uid, et.intake_pool_id)
        cleaned = validate_intake_answers(pool, body.answers)
        return {"ok": True, "required": True, "answers": cleaned}
    except IntakeDisqualified as exc:
        raise HTTPException(status_code=422, detail={"code": "intake_disqualified", "message": str(exc)}) from exc
    except (IntakeError, IsolationError, LookupError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/public/hosts/{public_slug}/bookings", status_code=201)
async def public_create_booking(public_slug: str, body: PublicBookingCreate) -> dict[str, Any]:
    profile = _resolve_public_host(public_slug)
    uid = str(profile["user_id"])
    ensure_default_consultation(uid)
    try:
        et = SlotEngine().resolve_event_type(uid, event_type_id=body.event_type_id, slug=body.event_type_slug)
        intake_answers = body.intake_answers
        if et.intake_pool_id:
            pool = vical_store.get_intake_pool(uid, et.intake_pool_id)
            intake_answers = validate_intake_answers(pool, body.intake_answers)
        result = book_with_saga(
            uid,
            event_type_id=et.id,
            guest_name=body.guest_name,
            guest_email=body.guest_email,
            starts_at=body.starts_at,
            ends_at=body.ends_at,
            source="public",
            notes=body.notes,
            intake_answers=intake_answers,
            holder_token=body.holder_token,
            lock_id=body.lock_id,
            workspace_id=uid,
            prefer_managed_zoom=True,
        )
        booking = result["booking"]
    except IntakeDisqualified as exc:
        raise HTTPException(status_code=422, detail={"code": "intake_disqualified", "message": str(exc)}) from exc
    except IntakeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BookingLifecycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (LookupError, IsolationError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    payload = to_public_booking_view(booking.to_dict())
    payload["conferenceManaged"] = result.get("conferenceManaged")
    payload["duplicate"] = result.get("duplicate")
    if booking.status == "pending_payment":
        try:
            checkout = create_checkout_session(uid, booking.id)
            payload["checkout"] = checkout
        except DepositError:
            pass
    return payload


@router.post("/public/cancel")
async def public_cancel(
    guest_token: str | None = Query(None),
    body: PublicCancel | None = None,
) -> dict[str, Any]:
    token = guest_token or (body.guest_token if body else None)
    if not token:
        raise HTTPException(status_code=400, detail="guest_token required")
    try:
        return BookingLifecycle().cancel_by_guest_token(token, reason=body.reason if body else None).to_dict()
    except BookingLifecycleError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/public/reschedule")
async def public_reschedule(body: PublicReschedule) -> dict[str, Any]:
    booking = vical_store.get_booking_by_guest_token(body.guest_token)
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    try:
        return (
            BookingLifecycle()
            .reschedule(booking.user_id, booking.id, starts_at=body.starts_at, ends_at=body.ends_at)
            .to_dict()
        )
    except BookingLifecycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/public/bookings/by-token")
async def public_booking_by_token(guest_token: str = Query(...)) -> dict[str, Any]:
    booking = vical_store.get_booking_by_guest_token(guest_token)
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    et = vical_store.get_event_type(booking.user_id, booking.event_type_id)
    payload = booking.to_dict()
    # Guest-safe: keep token; strip host-private metadata keys if needed
    payload["event_type"] = {"id": et.id, "slug": et.slug, "name": et.name, "duration_minutes": et.duration_minutes}
    return payload


@router.get("/public/bookings/by-token/ics")
async def public_booking_ics(guest_token: str = Query(...)) -> Response:
    booking = vical_store.get_booking_by_guest_token(guest_token)
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    if booking.status != "confirmed":
        raise HTTPException(status_code=400, detail="ICS available for confirmed bookings only")
    et = vical_store.get_event_type(booking.user_id, booking.event_type_id)
    doc = booking_ics_dict(booking, title=f"{et.name}: {booking.guest_name}")
    return Response(
        content=doc["body"],
        media_type=doc["content_type"],
        headers={"Content-Disposition": f'attachment; filename="{doc["filename"]}"'},
    )


@router.get("/deposits/mock-pay")
async def deposit_mock_pay(session_id: str = Query(...)) -> dict[str, Any]:
    try:
        booking = mark_deposit_paid(session_id=session_id)
    except DepositError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "booking": booking.to_dict()}


@router.post("/webhooks/zoom")
async def zoom_webhook(
    request: Request,
    x_zm_signature: str | None = Header(default=None, alias="x-zm-signature"),
    x_zm_request_timestamp: str | None = Header(default=None, alias="x-zm-request-timestamp"),
) -> dict[str, Any]:
    import json

    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        payload = {}
    result = handle_zoom_webhook(
        payload=payload if isinstance(payload, dict) else {},
        body=raw,
        timestamp=x_zm_request_timestamp,
        signature=x_zm_signature,
    )
    if result.get("challenge"):
        return {
            "plainToken": result.get("plainToken"),
            "encryptedToken": result.get("encryptedToken"),
        }
    if not result.get("ok"):
        raise HTTPException(status_code=401, detail=result)
    return result


@router.post("/webhooks/google-calendar")
async def google_calendar_webhook(request: Request) -> dict[str, Any]:
    import json

    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8") or "{}") if raw else {}
    except Exception:
        payload = {}
    headers = {k: v for k, v in request.headers.items()}
    result = handle_google_calendar_webhook(
        headers=headers,
        body=payload if isinstance(payload, dict) else {},
    )
    if not result.get("ok"):
        raise HTTPException(status_code=401, detail=result)
    return result


@router.get("/bookings/{booking_id}/invitation")
async def booking_invitation(
    booking_id: str, user: dict = Depends(get_current_user)
) -> dict[str, Any]:
    booking = vical_store.get_booking(_uid(user), booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    ws = booking.workspace_id or booking.user_id
    projection = get_projection_store().get_projection(ws, booking_id)
    return {
        "bookingId": booking_id,
        "invitation": booking_invitation_view(projection),
        "projection": projection,
        "deliveryAttempts": get_projection_store().list_delivery_attempts(ws, booking_id),
    }


@router.post("/calendar/watches/renew")
async def renew_calendar_watches(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = _uid(user)
    renewed = renew_expiring_watches()
    return {"ok": True, "renewed": renewed}
