"""Stripe webhook event handlers (idempotent)."""

from __future__ import annotations

from typing import Any

from keprix.billing.invoicing.generator import generate_invoice_html
from keprix.billing.store import get_billing_store
from keprix.billing.subscriptions.dunning import clear_dunning, record_payment_failure
from keprix.billing.subscriptions.lifecycle import activate_subscription, cancel_subscription, start_trial


async def handle_checkout_completed(event: dict[str, Any]) -> dict[str, Any]:
    obj = event.get("data", {}).get("object", {})
    metadata = obj.get("metadata") or {}
    user_id = str(metadata.get("user_id") or "")
    plan_id = str(metadata.get("plan_id") or "")
    if not user_id or not plan_id:
        return {"ok": False, "reason": "missing metadata"}
    sub = await activate_subscription(user_id, plan_id=plan_id, stripe_subscription_id=obj.get("subscription"))
    return {"ok": True, "subscription": sub}


async def handle_subscription_created(event: dict[str, Any]) -> dict[str, Any]:
    obj = event.get("data", {}).get("object", {})
    metadata = obj.get("metadata") or {}
    user_id = str(metadata.get("user_id") or "")
    plan_id = str(metadata.get("plan_id") or "")
    if user_id and plan_id:
        return {"ok": True, "subscription": await activate_subscription(user_id, plan_id=plan_id, stripe_subscription_id=obj.get("id"))}
    return {"ok": True, "skipped": True}


async def handle_subscription_updated(event: dict[str, Any]) -> dict[str, Any]:
    obj = event.get("data", {}).get("object", {})
    metadata = obj.get("metadata") or {}
    user_id = str(metadata.get("user_id") or "")
    if not user_id:
        return {"ok": True, "skipped": True}
    status = str(obj.get("status") or "active")
    return {
        "ok": True,
        "subscription": await get_billing_store().save_subscription(
            user_id,
            {
                "status": status,
                "stripe_subscription_id": obj.get("id"),
                "cancel_at_period_end": bool(obj.get("cancel_at_period_end")),
            },
        ),
    }


async def handle_subscription_deleted(event: dict[str, Any]) -> dict[str, Any]:
    obj = event.get("data", {}).get("object", {})
    metadata = obj.get("metadata") or {}
    user_id = str(metadata.get("user_id") or "")
    if not user_id:
        return {"ok": True, "skipped": True}
    return {"ok": True, "subscription": await cancel_subscription(user_id, at_period_end=False)}


async def handle_invoice_paid(event: dict[str, Any]) -> dict[str, Any]:
    obj = event.get("data", {}).get("object", {})
    metadata = obj.get("metadata") or {}
    user_id = str(metadata.get("user_id") or obj.get("customer_email") or "unknown")
    amount = int(obj.get("amount_paid") or obj.get("total") or 0)
    lines = obj.get("lines") or {}
    line_items = lines.get("data") if isinstance(lines, dict) else []
    first_line = line_items[0] if isinstance(line_items, list) and line_items else {}
    description = str(first_line.get("description") or "Subscription") if isinstance(first_line, dict) else "Subscription"
    html = generate_invoice_html(
        invoice_number=str(obj.get("number") or obj.get("id")),
        customer_name=str(obj.get("customer_name") or user_id),
        customer_email=str(obj.get("customer_email") or ""),
        description=description,
        subtotal=amount,
        tax_amount=int(obj.get("tax") or 0),
        total=amount,
        currency=str(obj.get("currency") or "gbp"),
        status="paid",
    )
    invoice = await get_billing_store().save_invoice(
        {
            "user_id": user_id,
            "number": str(obj.get("number") or obj.get("id")),
            "status": "paid",
            "currency": str(obj.get("currency") or "gbp"),
            "subtotal": amount,
            "tax_amount": int(obj.get("tax") or 0),
            "total": amount,
            "stripe_invoice_id": obj.get("id"),
            "html_body": html,
        }
    )
    if user_id != "unknown":
        await clear_dunning(user_id)
    return {"ok": True, "invoice": invoice}


async def handle_invoice_payment_failed(event: dict[str, Any]) -> dict[str, Any]:
    obj = event.get("data", {}).get("object", {})
    metadata = obj.get("metadata") or {}
    user_id = str(metadata.get("user_id") or "")
    if not user_id:
        return {"ok": True, "skipped": True}
    return {"ok": True, "dunning": await record_payment_failure(user_id)}


async def handle_trial_will_end(event: dict[str, Any]) -> dict[str, Any]:
    obj = event.get("data", {}).get("object", {})
    metadata = obj.get("metadata") or {}
    user_id = str(metadata.get("user_id") or "")
    plan_id = str(metadata.get("plan_id") or "")
    if user_id and plan_id:
        await get_billing_store().save_subscription(user_id, {"trial_notice_sent": True})
    return {"ok": True}


HANDLERS: dict[str, Any] = {
    "checkout.session.completed": handle_checkout_completed,
    "customer.subscription.created": handle_subscription_created,
    "customer.subscription.updated": handle_subscription_updated,
    "customer.subscription.deleted": handle_subscription_deleted,
    "invoice.paid": handle_invoice_paid,
    "invoice.payment_failed": handle_invoice_payment_failed,
    "invoice.payment_succeeded": handle_invoice_paid,
    "invoice.upcoming": lambda event: {"ok": True, "reminder": True},
    "customer.subscription.trial_will_end": handle_trial_will_end,
    "payment_method.attached": lambda event: {"ok": True},
    "payment_method.detached": lambda event: {"ok": True},
    "charge.refunded": lambda event: {"ok": True},
    "charge.dispute.created": lambda event: {"ok": True, "review_required": True},
}
