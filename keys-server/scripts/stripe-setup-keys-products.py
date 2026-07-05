#!/usr/bin/env python3
"""Create Stripe products for Petraclus subscriptions.

Run: STRIPE_SECRET_KEY=sk_test_... python scripts/stripe-setup-keys-products.py
"""
from __future__ import annotations

import os
import sys

import stripe

PRODUCTS = [
    {
        "name": "Petraclus",
        "description": "AI-native cyber operations platform",
        "metadata": {"product": "petraclus"},
        "prices": [
            {"env": "STRIPE_PRICE_PETRA_PRO_MONTHLY", "nickname": "Petraclus Pro monthly", "amount": 5900, "tier": "PRO", "interval": "month"},
            {"env": "STRIPE_PRICE_PETRA_PRO_ANNUAL", "nickname": "Petraclus Pro annual", "amount": 59000, "tier": "PRO", "interval": "year"},
            {"env": "STRIPE_PRICE_PETRA_TEAM_MONTHLY", "nickname": "Petraclus Team monthly", "amount": 15900, "tier": "TEAM", "interval": "month"},
            {"env": "STRIPE_PRICE_PETRA_TEAM_ANNUAL", "nickname": "Petraclus Team annual", "amount": 159000, "tier": "TEAM", "interval": "year"},
        ],
    },
]


def main() -> None:
    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        print("Set STRIPE_SECRET_KEY", file=sys.stderr)
        sys.exit(1)

    client = stripe.StripeClient(secret)

    for product_def in PRODUCTS:
        product = client.products.create(
            params={
                "name": product_def["name"],
                "description": product_def["description"],
                "metadata": product_def["metadata"],
            }
        )
        print(f"\n# {product_def['name']} ({product.id})")
        for price_def in product_def["prices"]:
            interval = price_def.get("interval", "month")
            price = client.prices.create(
                params={
                    "product": product.id,
                    "unit_amount": price_def["amount"],
                    "currency": "gbp",
                    "recurring": {"interval": interval},
                    "nickname": price_def["nickname"],
                    "metadata": {
                        **product_def["metadata"],
                        "tier": price_def["tier"],
                        "interval": interval,
                    },
                }
            )
            print(f"{price_def['env']}={price.id}")

    print("\n# Webhook: https://keys.petraclus.uk/api/v1/stripe/webhook")
    print("# Events: checkout.session.completed, customer.subscription.deleted, invoice.payment_failed")


if __name__ == "__main__":
    main()
