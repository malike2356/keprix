# Prompt 413 / 10: Billing promo, trial, tenant BYOK

Status: COMPLETED 2026-08-04
Series: Keprix close Carina parity gaps  
Depends on: 405 / 02  
Blocks: 415  
Severity: LOW  
Owner gates: Stripe price IDs from `.access` only; no new Prices unless owner asks.  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Carina has promo/trial depth and per-tenant BYOK. Keprix billing is strong on subscriptions/wallets/donations.

## Goal

1. Promo code redemption against existing catalog prices.
2. Trial flag on subscription plans already in catalog.
3. Per-tenant/provider API key vaulting for BYOK (never log secrets).

## Must-haves

1. Promo redeem API + tests with fake catalog.
2. Trial days respected in checkout when plan supports it.
3. BYOK store encrypted/via vault pattern; agent tools must not echo keys.

## Acceptance

- [x] No new Stripe Prices created in Hub.
- [x] Secrets never appear in chat/logs/docs.
