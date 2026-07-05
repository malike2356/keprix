# keys.petraclus.uk

Licence key server for **Petraclus** Pro/Team tiers and Scout promo entitlement delivery.

keprix has no remote licence keys. Commercial Aiva keys stay outside this workspace.

## Stripe setup

1. Copy `.env.example` to `.env` and set `STRIPE_SECRET_KEY` (test mode first).
2. Create products:

```bash
cd /opt/lampp/htdocs/verlox/keprix-ai/keys-server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
STRIPE_SECRET_KEY=sk_test_... python scripts/stripe-setup-keys-products.py
```

3. Paste printed price IDs into `.env`.
4. In Stripe Dashboard, add webhook endpoint:
   - URL: `https://keys.petraclus.uk/api/v1/webhooks/stripe`
   - Events: `checkout.session.completed`, `customer.subscription.deleted`, `invoice.payment_failed`
5. Set `STRIPE_WEBHOOK_SECRET` from the webhook signing secret.

## Local run

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8080
curl http://localhost:8080/health
```

## Scope

- `PETRA-PRO-*` and `PETRA-TEAM-*` key generation and validation
- Scout 50% first-year promo codes for Petraclus Pro/Team subscribers
- Does **not** issue keprix or Aiva keys
