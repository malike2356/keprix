# Billing and subscription (workspace UI)

Keprix can run SaaS-style subscription billing when configured. The signed-in workspace hub is at **`/settings/billing`**.

## Enable billing locally

```bash
KEPRIX_BILLING_ENABLED=true
KEPRIX_BILLING_USE_EXAMPLE=true
KEPRIX_BILLING_CONFIG=config/billing.example.yaml
KEPRIX_STRIPE_CREDENTIALS_FILE=/path/to/your-stripe-prices.md
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
KEPRIX_INSTANCE_URL=http://localhost:3000
```

Mock mode works without Stripe for account and trial UI. Checkout and payment-method redirects require Stripe test keys.

## Price catalog (operator-owned)

Keprix is open source. **No live Stripe price IDs ship in the repo.** Operators provide their own catalog via `KEPRIX_STRIPE_CREDENTIALS_FILE` (markdown with `Label: price_…` lines) and pin IDs in `config/billing.yaml` (gitignored).

- Never create new Stripe products or prices unless you own the Stripe account and intend to.
- Checkout uses the pinned `stripe_price_id`; the UI formats amounts returned by the API.
- `config/billing.example.yaml` uses placeholders such as `price_YOUR_PRO_MONTH` only.

If your credentials file also lists other products (Scout, Carina, Aiva, …), the admin pricing dropdown **defaults to Keprix-relevant sections only** (`#Keprix…`, `#Verlox SaaS…`, `#Generic Verlox…`). Override with `KEPRIX_STRIPE_CATALOG_SCOPE=all` or `KEPRIX_STRIPE_CATALOG_SECTIONS=…` if needed.

## Admin pricing GUI

Admins and owners can pin catalog prices from **`/settings/billing`** without editing YAML by hand.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/billing/admin/catalog` | List Keprix-scoped catalog entries (`?scope=all` for full file) |
| GET | `/api/billing/admin/pricing` | Current plan price pins and write path |
| PUT | `/api/billing/admin/pricing` | Save plan pins into `billing.yaml` |

Amounts hydrate from catalog labels. Unknown price IDs are rejected. Market readiness fails when paid plan/addon pins are missing; see [Readiness](../operations/readiness.md).

## Community coffee donation

Optional open-amount Checkout (`POST /api/billing/donation/checkout` with `{ amount_gbp }`, min £1) via Stripe `price_data`. No catalog price per amount. Never gates Community Edition.

## Plans and portal

Workspace users see plan cards, invoices, seats, and Stripe Customer Portal links when billing is enabled and configured.
