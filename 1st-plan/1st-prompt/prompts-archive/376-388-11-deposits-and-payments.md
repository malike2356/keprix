# Prompt 387 / 11: Deposits and payments (owner gate)

Status: COMPLETED 2026-08-04
Series: Keprix viCal booking adoption  
Depends on: 379 / 03, 380 / 04, owner explicit go-ahead for live Stripe  
Blocks: 388 (optional; programme can archive without 11)  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Propreneur supports Stripe Checkout deposits and refunds for paid event types. Keprix Community already has Stripe donation rails. Deposits must reuse existing price IDs from `.access`, never invent prices.

## Goal

Optional paid event types: hold slot -> Checkout -> complete booking on paid webhook; refunds from hub for operators with billing permission.

## Baseline (do not reinvent)

| Piece | Path |
|---|---|
| Propreneur deposits | `VcalDepositCheckoutService.php`, completion/refund services |
| Help | `resources/docs/help/vcal-bookings/07-booking-payments.md` |
| Keprix billing | existing `/api/billing/*`, donation checkout patterns |
| Stripe SoT | `/opt/lampp/htdocs/verlox/.access/.stripe-credentials-and-price-id.md` |

## Must-haves

1. **Owner gate:** do not create Stripe Prices/Products from code. Map deposit amounts to existing price IDs or use `price_data` only if that is already the documented Keprix pattern for one-off amounts (coffee donation style). Prefer existing catalog IDs when present.
2. Flow: create booking `pending_payment` + slot lock -> Checkout session -> webhook marks paid + transitions to `pending_review` or `confirmed`.
3. Expired unpaid bookings auto-cancel + release lock.
4. Hub: retry pay link, refund action with audit.
5. Never log full card data or secret keys; never paste secrets into chat/docs.
6. Tests with Stripe test doubles / recorded fixtures.

## Nice-to-haves

1. Application fee / Connect (Propreneur env knobs) only if Keprix already has Connect.

## Ultimate

1. Accounting journals (Propreneur-only; do not port).

## Acceptance

- [ ] Unpaid booking cannot become confirmed.
- [ ] Successful test webhook confirms booking and creates calendar event.
- [ ] No new Stripe prices created in Hub during implementation unless owner ordered them in writing.
- [ ] Docs warn operators how to map amounts to existing prices.
