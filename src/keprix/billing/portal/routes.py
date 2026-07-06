"""Customer self-service billing portal routes."""

from __future__ import annotations

import json
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.billing.config_loader import billing_enabled, load_billing_config
from keprix.billing.feature_gates.matrix import build_feature_matrix
from keprix.billing.invoicing.history import get_invoice_for_user, list_billing_history
from keprix.billing.stripe.customer_portal import create_customer_portal_session
from keprix.billing.store import get_billing_store
from keprix.billing.stripe.checkout import create_checkout_session
from keprix.billing.subscriptions.lifecycle import cancel_subscription, start_trial
from keprix.billing.subscriptions.seats import invite_seat, remove_seat
from keprix.billing.webhooks.dispatcher import dispatch_webhook_event, verify_stripe_signature

router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutBody(BaseModel):
    plan_id: str
    interval: str | None = "month"


class UpgradeBody(BaseModel):
    plan_id: str
    interval: str | None = "month"


class CancelBody(BaseModel):
    at_period_end: bool = True


class SeatInviteBody(BaseModel):
    email: str = Field(..., min_length=3)
    role: str = "member"


def _user_id(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


def _require_billing() -> None:
    if not billing_enabled():
        raise HTTPException(status_code=404, detail="Billing is not enabled for this instance")


def _serialize_plans() -> list[dict[str, Any]]:
    cfg = load_billing_config()
    if cfg is None:
        return []
    return [
        {
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "prices": [price.model_dump() for price in plan.resolved_prices()],
            "seats": plan.seats,
            "metadata": dict(plan.metadata or {}),
            "feature_flags": dict(plan.feature_flags or {}),
        }
        for plan in cfg.plans
    ]


@router.get("/status")
async def billing_status() -> dict[str, Any]:
    cfg = load_billing_config()
    if cfg is None or not billing_enabled():
        return {"enabled": False}
    provider = os.environ.get("KEPRIX_BILLING_PROVIDER", "").strip().lower()
    if not provider:
        provider = "stripe" if os.environ.get("STRIPE_SECRET_KEY", "").strip() else "mock"
    return {
        "enabled": True,
        "provider": provider,
        "product_id": cfg.product.id,
        "product_name": cfg.product.name,
        "trial_days": cfg.product.trial_days,
        "plans": _serialize_plans(),
    }


@router.get("/portal/account")
async def portal_account(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _require_billing()
    uid = _user_id(user)
    sub = await get_billing_store().get_subscription(uid)
    customer = await get_billing_store().get_customer(uid)
    cfg = load_billing_config()
    return {
        "product": cfg.product.model_dump() if cfg else None,
        "subscription": sub,
        "customer": customer,
        "feature_matrix": build_feature_matrix(),
        "plans": _serialize_plans(),
    }


@router.get("/portal/invoices")
async def portal_invoices(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _require_billing()
    items = await list_billing_history(_user_id(user))
    return {"items": items}


@router.get("/portal/invoices/{invoice_id}")
async def portal_invoice(invoice_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _require_billing()
    invoice = await get_invoice_for_user(_user_id(user), invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/portal/checkout")
async def portal_checkout(body: CheckoutBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _require_billing()
    email = str(user.get("email") or f"{_user_id(user)}@local")
    return await create_checkout_session(
        user_id=_user_id(user),
        email=email,
        plan_id=body.plan_id,
        interval=body.interval,
    )


@router.post("/portal/upgrade")
async def portal_upgrade(body: UpgradeBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _require_billing()
    email = str(user.get("email") or f"{_user_id(user)}@local")
    return await create_checkout_session(
        user_id=_user_id(user),
        email=email,
        plan_id=body.plan_id,
        interval=body.interval,
    )


@router.post("/portal/cancel")
async def portal_cancel(body: CancelBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _require_billing()
    sub = await cancel_subscription(_user_id(user), at_period_end=body.at_period_end)
    return {"ok": True, "subscription": sub}


@router.post("/portal/resume")
async def portal_resume(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _require_billing()
    sub = await get_billing_store().save_subscription(_user_id(user), {"cancel_at_period_end": False, "status": "active"})
    return {"ok": True, "subscription": sub}


@router.get("/portal/payment-method")
async def portal_payment_method(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _require_billing()
    customer = await get_billing_store().get_customer(_user_id(user))
    return {"stripe_customer_id": customer.get("stripe_customer_id") if customer else None}


@router.post("/portal/payment-method")
async def portal_payment_method_update(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _require_billing()
    try:
        return await create_customer_portal_session(_user_id(user))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/portal/seats")
async def portal_seats(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _require_billing()
    seats = await get_billing_store().list_seats(_user_id(user))
    return {"items": seats}


@router.post("/portal/seats/invite")
async def portal_seat_invite(body: SeatInviteBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _require_billing()
    try:
        seat = await invite_seat(_user_id(user), email=body.email, role=body.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "seat": seat}


@router.delete("/portal/seats/{seat_id}")
async def portal_seat_remove(seat_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _require_billing()
    removed = await remove_seat(_user_id(user), seat_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Seat not found")
    return {"ok": True}


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict[str, Any]:
    _require_billing()
    payload = await request.body()
    if not verify_stripe_signature(payload, request.headers.get("stripe-signature")):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    event = json.loads(payload.decode("utf-8"))
    return await dispatch_webhook_event(event)


@router.post("/portal/trial")
async def portal_start_trial(body: UpgradeBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _require_billing()
    sub = await start_trial(_user_id(user), body.plan_id)
    return {"ok": True, "subscription": sub}
