"""Team seat invitations and limits."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.billing.config_loader import load_billing_config
from keprix.billing.store import get_billing_store

logger = logging.getLogger(__name__)


async def seat_limit_for_user(owner_id: str) -> int:
    sub = await get_billing_store().get_subscription(owner_id)
    if sub is None:
        cfg = load_billing_config()
        plan = cfg.community_plan() if cfg else None
        return plan.seats if plan else 1
    return int(sub.get("seats") or 1)


async def invite_seat(owner_id: str, *, email: str, role: str = "member") -> dict[str, Any]:
    seats = await get_billing_store().list_seats(owner_id)
    active = [s for s in seats if s.get("status") in {"invited", "active"}]
    limit = await seat_limit_for_user(owner_id)
    if len(active) >= limit:
        raise ValueError("Seat limit reached for current plan")

    expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    seat = await get_billing_store().save_seat(
        {
            "owner_id": owner_id,
            "email": email.strip().lower(),
            "role": role,
            "status": "invited",
            "invited_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires,
            "token": str(uuid.uuid4()),
        }
    )

    workspace_role = "admin" if role == "admin" else "user"
    try:
        from keprix.auth.user_invites import send_workspace_invite

        await send_workspace_invite(
            email=email,
            role=workspace_role,
            invited_by=owner_id,
            seat_id=str(seat.get("id")),
            owner_id=owner_id,
            message="You have been invited to join this Keprix team workspace.",
        )
    except Exception as exc:
        logger.warning("Billing seat invite email failed for %s: %s", email, exc)

    return seat


async def remove_seat(owner_id: str, seat_id: str) -> bool:
    seats = await get_billing_store().list_seats(owner_id)
    if not any(seat.get("id") == seat_id for seat in seats):
        return False
    return await get_billing_store().delete_seat(seat_id)
