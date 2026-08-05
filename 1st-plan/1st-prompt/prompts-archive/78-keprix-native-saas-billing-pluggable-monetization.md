# Keprix - Prompt 78: Native SaaS Billing; Pluggable Monetization Layer

## Context

Every product built on Keprix will be sold as SaaS. Rather than each product (Petraclus, AbbiS, Fleetz, NHS) building its own billing engine, Keprix provides a native, pluggable monetization layer. Products bring their Stripe credentials and pricing configuration. Keprix handles the rest.

This is NOT a Petraclus billing prompt. It is a Keprix platform capability. Any product that extends Keprix inherits billing with zero engineering work; just configuration.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/`

## Design Principle

> Products define WHAT to charge. Keprix handles HOW to charge.

A product author creates a YAML file with their plans, prices, and feature flags. Keprix auto-generates the Stripe products, checkout flow, customer portal, webhook handlers, subscription lifecycle, invoicing, and tax engine. The product never writes billing code.

## Architecture

```
KEPRIX BILLING LAYER
═══════════════════════════════════════════════

  ┌──────────────────────────────────────────┐
  │  PRODUCT CONFIG (YAML)                   │
  │  ─────────────────────────────────────── │
  │  plans:                                  │
  │    starter: £29/mo (feature_flags: {...})│
  │    pro:     £79/mo                       │
  │    team:    £199/mo                      │
  │  addons: extra_seats, storage, api       │
  │  tax: { regions: [UK, EU, US] }         │
  │  trial_days: 14                          │
  └──────────┬───────────────────────────────┘
             │  Auto-provisioned at startup
             ▼
  ┌──────────────────────────────────────────┐
  │  KEPRIX BILLING ENGINE                   │
  │  ─────────────────────────────────────── │
  │  Stripe product/pricing sync             │
  │  Checkout session management             │
  │  Subscription lifecycle                  │
  │  Customer portal API                     │
  │  Invoice generation (PDF)                │
  │  Dunning engine                          │
  │  Tax calculation (VAT/sales tax)         │
  │  Feature gate enforcement                │
  │  Team seat management                    │
  │  Webhook processing (13 events)          │
  └──────────┬───────────────────────────────┘
             │
     ┌───────┴───────┐
     ▼               ▼
  Stripe        Product Backend
  (payment)     (feature gates,
                 seat limits,
                 plan enforcement)
```

## Files To Create

```text
src/keprix/billing/
  __init__.py
  engine.py              # Billing engine bootstrap and orchestration
  config_loader.py       # Load product billing YAML, validate, provision
  schema.py              # Billing configuration schema (Pydantic)
  
  stripe/
    __init__.py
    client.py            # Stripe client wrapper (multi-product)
    products.py          # Sync product config → Stripe products/prices
    checkout.py          # Create and manage Stripe Checkout sessions
    webhooks.py          # Process 13 Stripe webhook event types
    customer_portal.py   # Stripe Customer Portal session management
    
  subscriptions/
    __init__.py
    lifecycle.py         # Trial → Active → Past_due → Cancelled → Expired
    dunning.py           # Failed payment retry with escalation
    provisioning.py      # Activate/deactivate features on plan change
    seats.py             # Team seat lifecycle management
    
  invoicing/
    __init__.py
    generator.py         # Invoice PDF generation (WeasyPrint)
    templates.py         # Invoice and receipt templates
    history.py           # Billing history API
    
  tax/
    __init__.py
    calculator.py        # VAT/sales tax calculation by region
    validator.py         # VAT ID validation (VIES, HMRC)
    rates.py             # Tax rate table per region
    
  feature_gates/
    __init__.py
    enforcer.py          # Check feature access against active plan
    matrix.py            # Feature gate matrix builder from config
    middleware.py         # FastAPI middleware for feature enforcement
    
  webhooks/
    __init__.py
    dispatcher.py        # Route Stripe events to handlers
    handlers.py          # All webhook event handlers (idempotent)
    
  portal/
    __init__.py
    routes.py            # Customer self-service API
    account.py           # Account and billing info
    invoices.py          # Invoice list and download
    
models/
  billing.py             # Subscription, Invoice, PaymentMethod, FeatureFlag
  customer.py            # Customer → Stripe customer mapping
  plan.py                # Plan definition model

migrations/versions/
  XXX_billing_core.py    # Subscription and customer tables
  XXX_billing_invoices.py # Invoice and payment tables
  XXX_billing_seats.py    # Team seats table

config/
  billing.example.yaml   # Example billing configuration
  billing.schema.json    # JSON Schema for validation

tests/billing/
  test_config_loader.py
  test_checkout.py
  test_lifecycle.py
  test_dunning.py
  test_invoicing.py
  test_tax.py
  test_feature_gates.py
  test_webhooks.py
  test_seats.py
  test_portal.py
```

## Product Billing Configuration (YAML)

Every product built on Keprix provides a single `billing.yaml`:

```yaml
# billing.yaml; drop this in your product's config directory
# Keprix auto-provisions Stripe products, prices, and webhooks from this file

product:
  id: "petraclus"                    # Unique product identifier
  name: "Petraclus"                  # Display name on invoices
  company: "Verlox Ltd"              # Legal entity for invoices
  company_address: "Portsmouth, UK"  # Invoice address
  vat_number: ""                     # Company VAT number (if registered)
  support_email: "billing@petraclus.uk"
  website: "https://petraclus.uk"
  trial_days: 14                     # 0 = no trial

plans:
  - id: "community"
    name: "Community"
    description: "Free forever for individual security professionals"
    price: 0                         # 0 = free
    currency: "gbp"
    interval: null                   # null = forever free
    seats: 1
    metadata:
      highlight: false
    feature_flags:
      tools_all: true
      personas: [nexus, forge, warden, sage]
      workflows: 5
      governance: "local"
      audit_retention_days: 7
      support: "community"
      api_access: false
      sso: false
      dark_web_tools: false

  - id: "pro"
    name: "Pro"
    description: "For professional penetration testers"
    prices:
      - amount: 4900                 # In minor units: £49.00
        currency: "gbp"
        interval: "month"
      - amount: 49000                # £490.00/year (2 months free)
        currency: "gbp"
        interval: "year"
        discount_text: "Save 17%"
    seats: 1
    metadata:
      highlight: true                # Featured plan in checkout
      badge: "Most Popular"
    feature_flags:
      tools_all: true
      personas: [nexus, forge, warden, sage, beacon, prism, compass, ember, echo, codex, scout]
      workflows: 15
      governance: "full"
      audit_retention_days: 90
      support: "email"
      api_access: false
      sso: false
      dark_web_tools: true

  - id: "team"
    name: "Team"
    description: "For security teams and consultancies"
    prices:
      - amount: 12900
        currency: "gbp"
        interval: "month"
      - amount: 129000
        currency: "gbp"
        interval: "year"
        discount_text: "Save 17%"
    seats: 10
    metadata:
      highlight: false
    feature_flags:
      tools_all: true
      personas: [nexus, forge, warden, sage, beacon, prism, compass, ember, echo, codex, scout]
      workflows: 15
      governance: "full"
      audit_retention_days: 365
      support: "priority"
      api_access: true
      sso: false                      # sso is an addon below
      dark_web_tools: true

addons:
  - id: "extra_seats"
    name: "Extra Seats"
    description: "Additional team members beyond plan limit"
    price: 1500                       # £15.00/seat/month
    currency: "gbp"
    interval: "month"
    applies_to: ["team"]
    
  - id: "extended_audit"
    name: "Extended Audit Retention"
    description: "3-year audit log retention"
    price: 2900                       # £29.00/month
    currency: "gbp"
    interval: "month"
    applies_to: ["pro", "team"]
    
  - id: "sso"
    name: "Single Sign-On"
    description: "SAML/OIDC enterprise SSO"
    price: 9900                       # £99.00/month
    currency: "gbp"
    interval: "month"
    applies_to: ["team"]
    
  - id: "priority_sla"
    name: "Priority Support SLA"
    description: "4-hour response, phone support"
    price: 9900
    currency: "gbp"
    interval: "month"
    applies_to: ["team"]

tax:
  regions:
    - code: "GB"
      name: "United Kingdom"
      rate: 0.20                     # 20% VAT
      rule: "always"                  # "always", "b2b_reverse", "none"
      vat_validation: "hmrc"
    - code: "EU"
      name: "European Union"
      rate: null                      # Variable by country (VAT MOSS)
      rule: "b2b_reverse"
      vat_validation: "vies"
    - code: "US"
      name: "United States"
      rate: 0
      rule: "none"
    - code: "ROW"
      name: "Rest of World"
      rate: 0
      rule: "none"

dunning:
  enabled: true
  retry_schedule:
    - days: 1
      action: "retry"
    - days: 3
      action: "retry"
      notify: true
      notify_template: "payment_failed"
    - days: 7
      action: "retry"
      notify: true
      notify_template: "payment_failed"
      degrade_features: true          # Downgrade to next lower plan
    - days: 14
      action: "retry"
      notify: true
      notify_template: "payment_at_risk"
    - days: 30
      action: "cancel"

webhooks:
  signing_secret_env: "STRIPE_WEBHOOK_SECRET"
  events:
    - checkout.session.completed
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.paid
    - invoice.payment_failed
    - invoice.payment_succeeded
    - invoice.upcoming
    - customer.subscription.trial_will_end
    - payment_method.attached
    - payment_method.detached
    - charge.refunded
    - charge.dispute.created
```

## Auto-Provisioning Flow

On Keprix startup with a product's `billing.yaml`:

```
STARTUP:
  1. Load billing.yaml from active extension's config directory
  2. Validate against schema (Pydantic)
  3. Sync plans → Stripe products and prices
     - Create if not exists (match by metadata.product_id + plan_id)
     - Update if price changed → archive old, create new
     - Delete if plan removed from config
  4. Register webhook endpoint: /api/billing/webhook
  5. Create database tables (Alembic migration)
  6. Register feature gate middleware
  7. Mount customer portal routes: /api/billing/portal/*
  8. Log: "Billing engine ready for [product_name]; X plans, Y addons"

NO BILLING.YAML:
  - Feature gates return ALLOW for everything
  - No billing routes mounted
  - Log: "No billing config found; all features unrestricted"
```

## Subscription Lifecycle

```
  [User signs up]
       │
  TRIAL (14 days or configurable)
  ├── Full plan features
  ├── No payment method required
  ├── "Trial ends in X days" banner in portal
  └── Email: "Trial ending soon" at 7 and 3 days remaining
       │
  [User adds payment method]
       │
  ACTIVE
  ├── Features unlocked per plan
  ├── Monthly/annual billing
  ├── Portal shows next billing date
  └── Invoice generated on each payment
       │
  [Payment succeeds] → ACTIVE (renew)
  [Payment fails]    → PAST_DUE (dunning)
  [User cancels]     → ACTIVE (until period end) → CANCELLED → EXPIRED
  [User upgrades]    → Immediate upgrade, prorated charge
  [User downgrades]  → At period end, data preserved, features restricted
```

## Feature Gate Enforcement

```python
# Products define feature_flags in billing.yaml
# Keprix enforces them automatically

# In product code:
from keprix.billing.feature_gates import require_feature

@require_feature("tools_all")
async def execute_tool(tool_name: str, params: dict):
    ...

@require_feature("dark_web_tools")
async def run_onion_search(query: str):
    ...

@require_feature("api_access")
async def api_endpoint():
    ...

# Feature check in any context:
from keprix.billing.feature_gates import check_feature

if await check_feature("governance", min_value="full"):
    # Full governance features available
```

## Customer Portal API

```
GET    /api/billing/portal/account        → Current plan, status, next billing
GET    /api/billing/portal/invoices       → Invoice list with download links
GET    /api/billing/portal/invoices/{id}  → Single invoice PDF
POST   /api/billing/portal/checkout       → Create Stripe Checkout session
POST   /api/billing/portal/upgrade        → Upgrade to new plan
POST   /api/billing/portal/cancel         → Cancel subscription
POST   /api/billing/portal/resume         → Resume cancelled subscription
GET    /api/billing/portal/payment-method → Current payment method
POST   /api/billing/portal/payment-method → Update payment method
GET    /api/billing/portal/seats          → Team seat list
POST   /api/billing/portal/seats/invite   → Invite team member
DELETE /api/billing/portal/seats/{id}     → Remove team member
```

## Stripe Webhook Handlers

| Event | Handler | Idempotency Key |
|-------|---------|----------------|
| `checkout.session.completed` | Create customer + subscription + provision features | `checkout_{session_id}` |
| `customer.subscription.created` | Create subscription record, send welcome email | `sub_created_{subscription_id}` |
| `customer.subscription.updated` | Sync plan, seats, addons to database | `sub_updated_{subscription_id}` |
| `customer.subscription.deleted` | Begin cancellation flow | `sub_deleted_{subscription_id}` |
| `invoice.paid` | Log payment, generate receipt PDF, send email | `invoice_{invoice_id}` |
| `invoice.payment_failed` | Trigger dunning sequence | `invoice_{invoice_id}` |
| `invoice.payment_succeeded` | Clear dunning, restore features if degraded | `invoice_{invoice_id}` |
| `invoice.upcoming` | Send renewal reminder (7 days before) | `upcoming_{subscription_id}` |
| `customer.subscription.trial_will_end` | Send trial ending notification | `trial_end_{subscription_id}` |
| `payment_method.attached` | Update customer payment method, clear dunning warning | `pm_{payment_method_id}` |
| `payment_method.detached` | Warn if no backup method exists | `pm_{payment_method_id}` |
| `charge.refunded` | Log refund, adjust billing history | `charge_{charge_id}` |
| `charge.dispute.created` | Flag for manual review, pause subscription | `dispute_{dispute_id}` |

## Tax Engine

```python
# Automatic tax calculation on every invoice:

def calculate_tax(customer_country: str, customer_vat_id: str | None, amount: int) -> TaxResult:
    region = match_tax_region(customer_country)
    
    if region.rule == "none":
        return TaxResult(rate=0, amount=0, label="No tax applied")
    
    if region.rule == "b2b_reverse" and customer_vat_id:
        if validate_vat_id(customer_vat_id, region.vat_validation):
            return TaxResult(rate=0, amount=0, label="VAT reverse charge (B2B)")
    
    if region.rate:
        tax = round(amount * region.rate)
        return TaxResult(rate=region.rate, amount=tax, label=f"VAT {region.rate*100}%")
    
    # EU VAT MOSS: charge customer's local rate
    if region.code == "EU":
        local_rate = get_eu_vat_rate(customer_country)
        tax = round(amount * local_rate)
        return TaxResult(rate=local_rate, amount=tax, label=f"VAT {local_rate*100}% ({customer_country})")
```

## Team Seat Management

```
SEAT LIFECYCLE:
  ┌─────────────────────────────────────────┐
  │ Plan defines max seats (Community:1,    │
  │ Pro:1, Team:10)                         │
  │                                          │
  │ Owner invites member:                    │
  │   POST /api/billing/portal/seats/invite  │
  │   { email, role }                        │
  │                                          │
  │ Invitation sent (7-day expiry)           │
  │   ↓                                      │
  │ Invitee accepts → seat filled            │
  │ Invitee declines → seat freed            │
  │ Invitation expires → seat freed          │
  │                                          │
  │ Can't invite if at seat limit:           │
  │   → Prompt upgrade or add extra_seats    │
  │                                          │
  │ Remove member:                            │
  │   → Seat freed immediately               │
  │   → Member loses access immediately       │
  │   → Billing adjusted next cycle           │
  └─────────────────────────────────────────┘
```

## Invoice Design

```
┌──────────────────────────────────────────────┐
│  [PRODUCT LOGO]            INVOICE            │
│                                              │
│  [Company Name]            Invoice #: INV-001 │
│  [Company Address]         Date: 4 Jul 2026  │
│  VAT: [VAT Number]        Due: 4 Jul 2026   │
│                                              │
│  BILL TO:                                    │
│  [Customer Name]                             │
│  [Customer Email]                            │
│  [Billing Address]                           │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ Description          Qty   Amount    │    │
│  ├──────────────────────────────────────┤    │
│  │ Petraclus Pro (monthly)  1   £49.00 │    │
│  │ 4 Jul - 3 Aug 2026                  │    │
│  ├──────────────────────────────────────┤    │
│  │ Subtotal                    £49.00  │    │
│  │ VAT (20%)                    £9.80  │    │
│  │ Total                       £58.80  │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  Status: PAID  |  Method: Visa ••••4242     │
│  Paid on: 4 Jul 2026                         │
│                                              │
│  [Company Name] is registered in England.    │
│  VAT Registration: [VAT Number]              │
└──────────────────────────────────────────────┘
```

## Environment Variables (Product Brings These)

```bash
# Required for billing to activate:
KEPRIX_BILLING_PROVIDER=stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Optional:
STRIPE_TEST_MODE=true             # Use Stripe test keys
KEPRIX_BILLING_CURRENCY=gbp       # Default currency
KEPRIX_BILLING_TAX_DEFAULT=0.20   # Default VAT rate if not in config
```

## Verification

- [ ] Billing YAML validated against schema on load
- [ ] Stripe products and prices sync correctly from config
- [ ] Checkout session creates Stripe customer + subscription
- [ ] Trial auto-converts at end unless cancelled
- [ ] Payment failure triggers dunning: retry day 1, 3, 7, 14, cancel day 30
- [ ] Feature gate blocks access when plan doesn't include feature
- [ ] Upgrade immediate, downgrade at period end
- [ ] Invoice PDF renders with company details, VAT breakdown, payment status
- [ ] UK VAT (20%), EU VAT MOSS, US (0%), ROW (0%) calculated correctly
- [ ] VAT reverse charge applied when valid VAT ID provided (B2B)
- [ ] Team seat limit enforced; add-on seats billable
- [ ] All 13 webhook events processed idempotently
- [ ] Customer portal shows correct plan, status, history
- [ ] No billing code runs if billing.yaml is absent
- [ ] Two products (e.g., Petraclus + AbbiS) can have separate billing configs
- [ ] Tests pass for all modules
