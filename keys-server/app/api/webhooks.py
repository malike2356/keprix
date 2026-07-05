from __future__ import annotations

import stripe
from fastapi import APIRouter, Header, HTTPException, Request

from app.billing import dispatch_stripe_event
from app.core.config import settings

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])
legacy_router = APIRouter(prefix="/api/v1/stripe", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str]:
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook not configured")

    stripe.api_key = settings.stripe_secret_key
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload.decode("utf-8"),
            stripe_signature or "",
            settings.stripe_webhook_secret,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await dispatch_stripe_event(event)

    return {"status": "ok"}


@router.post("/stripe/webhook")
async def stripe_webhook_legacy(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str]:
    return await stripe_webhook(request, stripe_signature)


@legacy_router.post("/webhook")
async def stripe_webhook_legacy_documented(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str]:
    return await stripe_webhook(request, stripe_signature)
