"""Deposit scaffold for paid event types (no new Stripe catalog prices)."""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.vical.bookings import BookingLifecycle, BookingLifecycleError
from keprix.vical.store import IsolationError, VicalStore, vical_store
from keprix.vical.types import VcalBooking

logger = logging.getLogger(__name__)

META_CHECKOUT = "deposit_checkout"
META_SESSION = "stripe_checkout_session_id"
META_PAID_AT = "deposit_paid_at"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def unpaid_ttl_minutes() -> int:
    try:
        return max(5, int(os.environ.get("KEPRIX_VICAL_UNPAID_TTL_MIN") or "60"))
    except ValueError:
        return 60


def deposits_enabled() -> bool:
    return os.environ.get("KEPRIX_VICAL_DEPOSITS", "1").strip().lower() not in {"0", "false", "no", "off"}


class DepositError(ValueError):
    pass


def create_checkout_session(
    user_id: str,
    booking_id: str,
    *,
    store: VicalStore | None = None,
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> dict[str, Any]:
    """
    Scaffold Checkout for pending_payment bookings.

    Records a ``price_data``-shaped line item (currency + unit_amount) matching the
    Keprix donation pattern so operators never create Dashboard Prices from Hub UI.
    Live Stripe session creation is operator-gated; local mock-pay completes the flow in CE.
    """
    if not deposits_enabled():
        raise DepositError("deposits disabled")

    store = store or vical_store
    booking = store.get_booking(user_id, booking_id)
    if booking.status != "pending_payment":
        raise DepositError(f"booking status is {booking.status}, expected pending_payment")

    et = store.get_event_type(user_id, booking.event_type_id)
    if not et.requires_deposit:
        raise DepositError("event type does not require deposit")

    amount = int(et.deposit_minor or 0)
    currency = (et.deposit_currency or "gbp").lower()
    if amount <= 0:
        raise DepositError(
            "deposit_minor must be > 0; use price_data amounts only, never create Hub prices"
        )

    session_id = f"cs_test_vical_{secrets.token_hex(8)}"
    success = success_url or f"/book/thanks?booking_id={booking.id}"
    cancel = cancel_url or "/"

    # Scaffold: mock pay endpoint. Wire async StripeClient.create_checkout_session
    # with the same price_data when KEPRIX_VICAL_STRIPE_LIVE=1 and billing is bootstrapped.
    checkout_url = f"/api/vical/deposits/mock-pay?session_id={session_id}"

    meta = dict(booking.metadata or {})
    meta[META_CHECKOUT] = {
        "session_id": session_id,
        "amount_minor": amount,
        "currency": currency,
        "pricing": "price_data",
        "product_name": f"viCal deposit: {et.name}",
        "success_url": success,
        "cancel_url": cancel,
        "created_at": _now().isoformat(),
        "stripe_live": False,
    }
    meta[META_SESSION] = session_id
    store.update_booking(user_id, booking_id, metadata=meta)

    return {
        "ok": True,
        "booking_id": booking.id,
        "session_id": session_id,
        "checkout_url": checkout_url,
        "amount_minor": amount,
        "currency": currency,
        "pricing": "price_data",
        "stripe_live": False,
        "note": "Scaffold only. Uses price_data shape; no new Stripe Prices. Complete via mock-pay or webhook mark-paid.",
    }


def mark_deposit_paid(
    *,
    booking_id: str | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    store: VicalStore | None = None,
) -> VcalBooking:
    store = store or vical_store
    booking: VcalBooking | None = None
    if booking_id and user_id:
        booking = store.get_booking(user_id, booking_id)
    elif session_id:
        for row in store.bookings.values():
            if str((row.metadata or {}).get(META_SESSION) or "") == session_id:
                booking = row
                break
    if booking is None:
        raise DepositError("booking not found for deposit payment")

    if booking.status != "pending_payment":
        return booking

    meta = dict(booking.metadata or {})
    meta[META_PAID_AT] = _now().isoformat()
    store.update_booking(booking.user_id, booking.id, metadata=meta)

    et = store.get_event_type(booking.user_id, booking.event_type_id)
    life = BookingLifecycle(store=store)
    if et.requires_approval:
        return store.update_booking(booking.user_id, booking.id, status="pending_review")
    store.update_booking(booking.user_id, booking.id, status="pending_review")
    return life.approve(booking.user_id, booking.id)


def expire_unpaid_bookings(
    *,
    store: VicalStore | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    store = store or vical_store
    now = now or _now()
    ttl = timedelta(minutes=unpaid_ttl_minutes())
    cancelled: list[str] = []
    life = BookingLifecycle(store=store)
    for booking in list(store.bookings.values()):
        if booking.status != "pending_payment":
            continue
        created = booking.created_at or now
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created + ttl > now:
            continue
        try:
            life.cancel(booking.user_id, booking.id, reason="unpaid_expired")
            cancelled.append(booking.id)
        except (BookingLifecycleError, IsolationError):
            continue
    return {"cancelled": cancelled, "count": len(cancelled)}
