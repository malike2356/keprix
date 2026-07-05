"""Stripe webhook handling for Petraclus licences."""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Any

import httpx
import stripe

from app.core.config import settings
from app.core.key_generator import generate_key
from app.db import get_pool
from app.stripe_prices import PriceMapping, build_price_map

logger = logging.getLogger(__name__)


def _configure_stripe() -> None:
    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        raise RuntimeError("STRIPE_SECRET_KEY is not set")
    stripe.api_key = secret


def verify_webhook(payload: bytes, signature: str) -> stripe.Event:
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not set")
    return stripe.Webhook.construct_event(payload, signature, secret)


def resolve_price_mapping(price_id: str) -> PriceMapping | None:
    return build_price_map().get(price_id)


def _get_field(value: Any, field: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(field, default)
    return getattr(value, field, default)


def _get_nested(value: Any, *fields: str) -> Any:
    current = value
    for field in fields:
        current = _get_field(current, field)
        if current is None:
            return None
    return current


def _mask_key(key_value: str) -> str:
    return f"{key_value[:12]}***"


async def _resolve_customer_email(session: stripe.checkout.Session, customer_id: str) -> str | None:
    session_email = _get_field(session, "customer_email")
    if session_email:
        return str(session_email).strip().lower()

    customer_details_email = _get_nested(session, "customer_details", "email")
    if customer_details_email:
        return str(customer_details_email).strip().lower()

    customer = stripe.Customer.retrieve(str(customer_id))
    customer_email = _get_field(customer, "email")
    if customer_email:
        return str(customer_email).strip().lower()
    return None


async def _send_key_email(*, email: str, product: str, tier: str, key_value: str) -> None:
    if not settings.email_from:
        logger.warning("[billing] key email skipped because EMAIL_FROM is not set")
        return

    subject = f"Your {product} licence key"
    text = (
        f"Your {product} {tier} licence key is:\n\n"
        f"{key_value}\n\n"
        "Keep this key private. Contact contact@verlox.uk if you need help."
    )

    if settings.resend_api_key:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.email_from,
                    "to": [email],
                    "subject": subject,
                    "text": text,
                },
            )
            if response.status_code >= 400:
                logger.warning(
                    "[billing] resend delivery failed email=%s status=%s",
                    email,
                    response.status_code,
                )
        return

    if settings.smtp_host and settings.smtp_user and settings.smtp_pass:
        message = EmailMessage()
        message["From"] = settings.email_from
        message["To"] = email
        message["Subject"] = subject
        message.set_content(text)

        def send_smtp() -> None:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_pass)
                server.send_message(message)

        await asyncio.to_thread(send_smtp)
        return

    logger.warning("[billing] no email provider configured; issued key for %s was not emailed", email)


async def handle_checkout_completed(session: stripe.checkout.Session) -> None:
    subscription_id = _get_field(session, "subscription")
    customer_id = _get_field(session, "customer")
    if not subscription_id or not customer_id:
        logger.warning("checkout.session.completed missing subscription or customer")
        return

    _configure_stripe()
    subscription = stripe.Subscription.retrieve(str(subscription_id))
    price_id = subscription["items"]["data"][0]["price"]["id"]
    mapping = resolve_price_mapping(str(price_id))
    if not mapping:
        logger.info("Ignoring checkout for unmapped price %s", price_id)
        return

    email = await _resolve_customer_email(session, str(customer_id))
    if not email:
        logger.warning("checkout.session.completed missing customer email")
        return

    key_value = generate_key(mapping.product, mapping.tier)
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            account_id = await conn.fetchval(
                """
                INSERT INTO key_accounts (
                    email,
                    stripe_customer_id,
                    stripe_subscription_id,
                    product,
                    tier,
                    interval,
                    status
                )
                VALUES ($1, $2, $3, $4, $5, $6, 'active')
                ON CONFLICT (stripe_subscription_id) DO UPDATE SET
                    email = EXCLUDED.email,
                    stripe_customer_id = EXCLUDED.stripe_customer_id,
                    product = EXCLUDED.product,
                    tier = EXCLUDED.tier,
                    interval = EXCLUDED.interval,
                    status = 'active',
                    updated_at = now()
                RETURNING id
                """,
                email,
                str(customer_id),
                str(subscription_id),
                mapping.product,
                mapping.tier,
                mapping.interval,
            )
            await conn.execute(
                """
                UPDATE licence_keys
                SET status = 'revoked', revoked_at = now()
                WHERE account_id = $1 AND status = 'active'
                """,
                account_id,
            )
            await conn.execute(
                """
                INSERT INTO licence_keys (account_id, key_value, product, tier)
                VALUES ($1, $2, $3, $4)
                """,
                account_id,
                key_value,
                mapping.product,
                mapping.tier,
            )

    logger.info(
        "[billing] key issued product=%s tier=%s email=%s key_prefix=%s",
        mapping.product,
        mapping.tier,
        email,
        key_value[:12],
    )
    try:
        await _send_key_email(
            email=email,
            product=mapping.product,
            tier=mapping.tier,
            key_value=key_value,
        )
    except Exception:
        logger.exception("[billing] key email failed email=%s key_prefix=%s", email, key_value[:12])


async def handle_subscription_deleted(subscription: stripe.Subscription) -> None:
    subscription_id = str(_get_field(subscription, "id", ""))
    if not subscription_id:
        logger.warning("customer.subscription.deleted missing subscription id")
        return

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            account = await conn.fetchrow(
                """
                UPDATE key_accounts
                SET status = 'cancelled', updated_at = now()
                WHERE stripe_subscription_id = $1
                RETURNING id, email
                """,
                subscription_id,
            )
            if not account:
                logger.info("[billing] subscription cancelled but no account found subscription_id=%s", subscription_id)
                return
            await conn.execute(
                """
                UPDATE licence_keys
                SET status = 'revoked', revoked_at = now()
                WHERE account_id = $1 AND status = 'active'
                """,
                account["id"],
            )
    logger.info(
        "[billing] subscription cancelled subscription_id=%s email=%s",
        subscription_id,
        account["email"],
    )


async def handle_payment_failed(invoice: stripe.Invoice) -> None:
    logger.info("payment failed for invoice %s", _get_field(invoice, "id"))
    # Payment failure dunning and suspension policy is intentionally left manual for now.


async def dispatch_stripe_event(event: stripe.Event) -> None:
    data_object: Any = event.data.object

    if event.type == "checkout.session.completed":
        await handle_checkout_completed(data_object)
    elif event.type == "customer.subscription.deleted":
        await handle_subscription_deleted(data_object)
    elif event.type == "invoice.payment_failed":
        await handle_payment_failed(data_object)
