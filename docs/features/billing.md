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

## API surface

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

**LLM usage** (`/usage`) tracks token consumption and estimated model cost. **Billing** manages product subscriptions, Stripe checkout, invoices, and plan feature gates.
