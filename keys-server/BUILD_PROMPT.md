# Petraclus Keys Server - Build Prompt

## What This Is

`keys.petraclus.uk` is private infrastructure for Petraclus Pro and Team licence
keys. It also creates Scout first-year promo entitlements for eligible Petraclus
customers.

This service does not issue keprix keys. keprix is open source and uses local
developer identity only.

This service does not issue Aiva keys. Aiva belongs to the separate commercial
Carina workspace.

This service lives at:

```text
/opt/lampp/htdocs/verlox/keprix-ai/keys-server/
```

## Product Scope

| Product | Supported Here | Notes |
| --- | --- | --- |
| Petraclus Pro | Yes | Paid professional security tier |
| Petraclus Team | Yes | Paid team security tier |
| Petraclus Community | No remote key | Community edition should not require this server |
| keprix | No | No remote licence keys |
| Aiva | No | Managed by the commercial Carina stack |

## Key Format

```text
PETRA-{TIER}-{GROUP1}-{GROUP2}-{CHECKSUM}
```

Tiers:

- `PRO`
- `TEAM`
- `DEV` for internal testing only

Groups are uppercase alphanumeric strings. Avoid ambiguous characters if the
implementation supports a custom alphabet.

Example:

```text
PETRA-PRO-B8L2NK5V-W3G9R2QA-7F
```

## Database Schema

The service must persist accounts and issued licence keys.

```sql
CREATE TABLE key_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    stripe_customer_id TEXT NOT NULL,
    stripe_subscription_id TEXT NOT NULL UNIQUE,
    product TEXT NOT NULL,
    tier TEXT NOT NULL,
    interval TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX key_accounts_email_idx ON key_accounts(email);
CREATE INDEX key_accounts_customer_idx ON key_accounts(stripe_customer_id);

CREATE TABLE licence_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES key_accounts(id) ON DELETE CASCADE,
    key_value TEXT NOT NULL UNIQUE,
    product TEXT NOT NULL,
    tier TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ
);

CREATE INDEX licence_keys_account_idx ON licence_keys(account_id);
CREATE INDEX licence_keys_key_idx ON licence_keys(key_value);
```

## Stripe Price Mapping

Read Stripe price IDs from environment variables:

```text
STRIPE_PRICE_PETRA_PRO_MONTHLY
STRIPE_PRICE_PETRA_PRO_ANNUAL
STRIPE_PRICE_PETRA_TEAM_MONTHLY
STRIPE_PRICE_PETRA_TEAM_ANNUAL
```

When a Stripe checkout completes:

1. Resolve the checkout subscription and price ID.
2. Ignore unknown price IDs.
3. Create or update the key account.
4. Revoke any previous active key for that subscription account.
5. Generate a new Petraclus key.
6. Persist the key.
7. Email the key if an email provider is configured.

When a subscription is deleted:

1. Mark the account as `cancelled`.
2. Revoke active keys for that account.

When payment fails:

1. Log the event.
2. Leave suspension manual until a formal dunning policy is approved.

## API Endpoints

### Stripe Webhooks

```text
POST /api/v1/webhooks/stripe
POST /api/v1/webhooks/stripe/webhook
POST /api/v1/stripe/webhook
```

All Stripe webhook endpoints must verify the Stripe signature using
`STRIPE_WEBHOOK_SECRET`.

### Admin API

Admin endpoints require `ADMIN_TOKEN`.

```text
GET  /api/admin/keys
POST /api/admin/keys/generate
POST /api/admin/keys/{id}/revoke
GET  /api/admin/accounts
GET  /api/admin/stats
```

### Health

```text
GET /health
```

Response:

```json
{
  "status": "ok",
  "service": "keys.petraclus.uk"
}
```

## Key Generation Logic

`app/core/key_generator.py` must expose:

```python
def generate_petraclus_key(tier: str) -> str:
    ...

def generate_key(product: str, tier: str) -> str:
    if product == "petraclus":
        return generate_petraclus_key(tier)
    raise ValueError("Unknown product: this server only issues Petraclus keys.")
```

The implementation must not generate any non-Petraclus prefix.

## Scout Entitlement Delivery

Petraclus Pro and Team customers are eligible for a first-year Scout promo.

Minimum implementation:

1. Store enough account and subscription metadata to identify eligible customers.
2. Keep Scout promo delivery outside key validation.
3. Do not mention keprix discounts.
4. Do not mention Aiva entitlements.

Scout integration can be added later as a separate module, but it must remain
Petraclus-only in this service.

## Configuration

Required environment variables:

```text
DATABASE_URL
KEY_SERVER_JWT_SECRET
KEY_SERVER_CHECKSUM_SECRET
ADMIN_TOKEN
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
```

Optional email delivery:

```text
RESEND_API_KEY
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASS
EMAIL_FROM
```

Optional Scout promo delivery:

```text
SCOUT_PROVISION_URL
SCOUT_PROVISION_SECRET
SCOUT_CONSOLE_PUBLIC_URL
```

Do not add `AIVA_*`, `CARINA_*`, or `keprix_*` licence variables to this service.

## Acceptance Criteria

- Checkout for a mapped Petraclus price creates one active `PETRA-*` key.
- Checkout for an unknown Stripe price does nothing.
- Subscription cancellation revokes active keys for the subscription account.
- keprix key generation raises an error.
- Aiva key generation raises an error.
- FastAPI title is `Petraclus Keys Server`.
- `/health` returns `keys.petraclus.uk`.
- No runtime route provisions Aiva workspaces.
- No key format uses a `CARINA-*` prefix.
- Tests cover key generation, unknown prices, successful checkout persistence,
  and subscription cancellation.
