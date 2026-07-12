# Billing and subscription (workspace UI)

Keprix can run SaaS-style subscription billing when configured. The signed-in workspace hub is at **`/settings/billing`**.

## Enable billing locally

```bash
KEPRIX_BILLING_ENABLED=true
KEPRIX_BILLING_USE_EXAMPLE=true
KEPRIX_BILLING_CONFIG=config/billing.example.yaml
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
KEPRIX_INSTANCE_URL=http://localhost:3000
```

Mock mode works without Stripe for account and trial UI. Checkout and payment-method redirects require Stripe test keys.

## Price catalog (do not invent prices)

All Stripe `price_*` IDs and amounts come from the Verlox catalog file
`.stripe-credentials-and-price-id.md` (repo root, not committed with secrets).

- Pin IDs in `config/billing.yaml` (or `billing.example.yaml` for local demos).
- Never create new Stripe products or prices unless the owner explicitly asks.
- Checkout uses the pinned `stripe_price_id`; the UI formats amounts returned by the API.

Example Pro pins (Verlox SaaS Pro): £49/month and £449/year. Team and addons follow the same catalog.

## Admin pricing GUI

Admins and owners can pin catalog prices from **`/settings/billing`** without editing YAML by hand.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/billing/admin/catalog` | List catalog entries from the credentials file |
| GET | `/api/billing/admin/pricing` | Current plan price pins and write path |
| PUT | `/api/billing/admin/pricing` | Save plan pins into `billing.yaml` |

Amounts hydrate from catalog labels. Invalid or unknown price IDs are rejected. Market readiness still fails when paid plan/addon pins are missing; see [Readiness](../operations/readiness.md).

## Workspace billing UI

- Subscription and payment method share a row; wallet and plans use the full width.
- Monthly/yearly toggle only applies when that interval exists for the plan. If a plan is monthly-only, the card says so and checkout uses the available interval.

## Managed AI credits vs BYOK

| Deployment | Token mode |
| --- | --- |
| Community / self-hosted | BYOK (bring your own provider keys). No managed wallet debit. |
| Hosted trial | Fixed trial credit + daily cap. Exhaustion offers BYOK or paid top-up; product stays available. |
| Hosted Pro / Team | Managed token wallet with monthly included credits + prepaid balance. |

Set `KEPRIX_HOSTED=true` on Verlox-hosted instances. Self-hosted operators leave it unset.

Wallet API:

| Method | Path |
| --- | --- |
| GET | `/api/billing/wallet/status` |
| GET | `/api/billing/wallet/ledger` |
| POST | `/api/billing/wallet/purchase` |

Credits are metered at provider cost x markup (default 2x), with 1 credit = 1 US cent of charged value. Unknown models use a conservative high price floor so Keprix never undercharges.

Top-up Stripe price IDs come only from the Verlox catalog (existing £5 / £10 / £20 prices). The Community coffee donation is voluntary open-amount Checkout (`POST /api/billing/donation/checkout` with `{ amount_gbp }`, min £1) via Stripe `price_data`. Never gates usage.

## Portal API surface

| Method | Path |
| --- | --- |
| GET | `/api/billing/status` |
| GET | `/api/billing/portal/account` |
| GET | `/api/billing/portal/invoices` |
| POST | `/api/billing/portal/checkout` |
| POST | `/api/billing/portal/trial` |
| POST | `/api/billing/portal/cancel` |
| POST | `/api/billing/portal/resume` |
| POST | `/api/billing/portal/payment-method` |

Backend package: `src/keprix/billing/`. Example config: `config/billing.example.yaml`.

## Distinction from LLM usage

**LLM usage** (`/usage`) tracks token consumption and estimated model cost for operators. **Billing** manages product subscriptions, Stripe checkout, invoices, and plan feature gates. **Managed AI wallet** (`/api/billing/wallet`) is the prepaid credit ledger for hosted managed tokens; it is separate from both.

## Related

- [Navigation and roles](navigation-and-roles.md) (commerce surfaces for non-admins)
- [Feature flags](feature-flags.md) (`commerce` progressive gate)
- [Readiness](../operations/readiness.md)
