# 300 - Open-amount Buy us a coffee donation

**Status:** COMPLETED (2026-07-12)
**Product:** Keprix
**Depends on:** existing `/api/billing/donation/checkout`, footer coffee link, Stripe catalog rule (no new catalog prices)

## Goal

The Community "Buy us a coffee" flow must stop being fixed at £1 only. £1 is the **minimum**. Users may donate any amount they choose (GBP).

## Direction (agreed)

1. Footer opens a **donate sheet** (dialog): presets £1 / £3 / £5 / £10 plus custom amount (min £1).
2. `POST /api/billing/donation/checkout` accepts `{ "amount_gbp": number, "donation_id"?: "coffee" }`.
3. Stripe Checkout uses inline **`price_data`** (`unit_amount` in pence, `currency: gbp`). Do **not** create new Stripe catalog prices.
4. Server validates `amount_gbp >= 1` and max £500. Convert to integer pence.
5. Keep donation voluntary; never gate features or readiness.
6. Existing £1 catalog price (`price_1Tri9T2WMXleLh8eA6gCXHbk`) remains documentary / optional default metadata only; open amounts use `price_data`.

## Shipped

| Piece | Path |
| --- | --- |
| Amount helper + `price_data` checkout | `src/keprix/billing/stripe/checkout.py` |
| Stripe client `price_data` support | `src/keprix/billing/stripe/client.py` |
| POST body `{ amount_gbp }` | `src/keprix/billing/portal/routes.py` |
| Donate sheet UI | `frontend/src/components/shell/DonateCoffeeSheet.tsx` |
| Footer trigger | `frontend/src/components/shell/WorkspaceFooter.tsx` |
| Client helper | `frontend/src/lib/billing-api.ts` (`createDonationCheckout`) |
| Tests | `tests/billing/test_checkout.py` |
| Docs / AGENTS | `docs/features/billing.md`, `AGENTS.md` |

## Validation

```bash
cd keprix
PYTHONPATH=src .venv/bin/python -m pytest tests/billing/test_checkout.py -q
# 6 passed
```

Manual: footer → Buy us a coffee → pick amount → Stripe Checkout shows chosen amount.
