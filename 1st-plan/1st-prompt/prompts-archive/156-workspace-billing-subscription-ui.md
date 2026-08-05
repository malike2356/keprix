# Keprix - Prompt 156: Workspace Billing and Subscription UI

## Context

Read archived Prompt **78** (`prompts-archive/78-keprix-native-saas-billing-pluggable-monetization.md`).

The **backend billing layer is shipped** under `src/keprix/billing/` with REST routes at
`/api/billing/portal/*`, Stripe checkout/portal redirects, feature gates, seats, and
invoicing. There is **no workspace UI** wired to those endpoints today.

Marketing `/pricing` still shows OSS "free forever" copy. Checkout success/cancel URLs
already default to `/settings/billing` (see `billing/stripe/checkout.py`), but that
page does not exist yet.

This prompt delivers the **signed-in workspace billing hub** so SaaS products built on
Keprix can sell subscriptions without custom frontend work.

**Out of scope:** Re-implementing Stripe logic (already in Prompt 78). **LLM usage**
(`/usage`, Prompt 147) is operational token/cost tracking; do not conflate with SaaS
subscription billing.

Depends on Prompts **78** (billing API), **103/116** (theme, cards), **136** (workspace
layout), **22** (app shell).

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Step 1: Billing status bootstrap (small backend addition)

Add a lightweight public-ish endpoint so the frontend can detect billing without
calling a portal route that 404s when disabled:

`GET /api/billing/status` (auth optional)

```json
{
  "enabled": true,
  "provider": "stripe",
  "product_id": "example-saas",
  "product_name": "Example SaaS",
  "trial_days": 14
}
```

When `billing_enabled()` is false, return `{ "enabled": false }` with HTTP 200 (not 404).

Extend `portal/account` response to include **`plans`** from `billing.yaml` (id, name,
description, prices, seats, metadata, feature_flags) so the UI can render plan cards
without a second config fetch. Keep secrets out of the payload.

File: `src/keprix/billing/portal/routes.py` (+ unit test in `tests/billing/test_portal.py`).

## Step 2: API client

`frontend/src/lib/billing-api.ts`

Types and functions (mirror existing portal routes):

```typescript
export type BillingStatus = { enabled: boolean; product_name?: string; ... };
export type BillingAccount = { product; subscription; customer; feature_matrix; plans? };
export type BillingPlan = { id; name; description; prices; seats; metadata; feature_flags };
export type BillingInvoice = { id; number; status; total; currency; created_at; ... };
export type BillingSeat = { id; email; role; status; ... };

export async function fetchBillingStatus(): Promise<BillingStatus>;
export async function fetchBillingAccount(): Promise<BillingAccount>;
export async function fetchBillingInvoices(): Promise<BillingInvoice[]>;
export async function fetchBillingInvoice(id: string): Promise<BillingInvoice>;
export async function startCheckout(planId: string, interval: "month" | "year"): Promise<{ checkout_url: string }>;
export async function startTrial(planId: string): Promise<BillingAccount>;
export async function upgradePlan(planId: string, interval?: string): Promise<{ checkout_url: string }>;
export async function cancelSubscription(atPeriodEnd?: boolean): Promise<void>;
export async function resumeSubscription(): Promise<void>;
export async function openPaymentMethodPortal(): Promise<{ portal_url: string }>;
export async function fetchSeats(): Promise<BillingSeat[]>;
export async function inviteSeat(email: string, role?: string): Promise<BillingSeat>;
export async function removeSeat(seatId: string): Promise<void>;
```

Use `ceApi` + `parseApiErrorMessage` (same pattern as `usage-api.ts`).

Checkout/portal helpers: `window.location.href = checkout_url` after POST; never embed
Stripe.js unless required (redirect flow is enough for v1).

## Step 3: Workspace page route

`frontend/src/app/(workspace)/settings/billing/page.tsx`

Use `PageHeader`, SWR, and MUI cards (match `settings/page.tsx` and `/usage` patterns).

### Layout sections

1. **Billing disabled state** (when `fetchBillingStatus().enabled === false`)
   - Explain that this instance runs without SaaS billing
   - Link to self-host docs and `/pricing` (OSS)
   - Do not error-loop on 404

2. **Current plan summary** (top card)
   - Plan name, status badge (`trialing`, `active`, `past_due`, `canceled`, none)
   - Trial countdown when `trial_ends_at` set
   - `current_period_end` renewal date
   - `cancel_at_period_end` warning with **Resume** button

3. **Plan picker** (when no paid plan or upgrade available)
   - Cards from `account.plans` + `feature_matrix`
   - Monthly/yearly toggle when multiple prices exist
   - Highlight `metadata.highlight` / `metadata.badge` from YAML
   - Actions per plan:
     - Free/community: **Start** or show "Current plan"
     - Paid: **Start trial** (`POST /portal/trial`) when trial configured and no sub
     - Paid: **Subscribe** / **Upgrade** -> checkout redirect
   - Feature comparison table (rows from union of `feature_flags` keys)

4. **Payment method**
   - Button **Manage payment method** -> `POST /portal/payment-method` redirect

5. **Invoices**
   - Table: date, number, status, total (formatted from minor units)
   - Row action: view/download when `html_body` or PDF link present
   - Empty state when no invoices

6. **Team seats** (when current plan `seats > 1`)
   - List seats, invite form (email + role), remove with confirm dialog
   - Show `seats used / seats included`

### Query param handlers

Stripe return URLs land on this page:

- `?checkout=success` -> success Alert + refetch account
- `?checkout=cancel` -> neutral Alert

Strip query params after display (`router.replace` without query).

## Step 4: Components

`frontend/src/components/billing/`:

| Component | Responsibility |
| --- | --- |
| `BillingPlanCard.tsx` | Single plan with price, CTA, feature bullets |
| `BillingPlanCompare.tsx` | Feature matrix table across plans |
| `BillingSubscriptionSummary.tsx` | Status, trial, renewal, cancel/resume |
| `BillingInvoiceTable.tsx` | Invoice list |
| `BillingSeatsPanel.tsx` | Seat list + invite |
| `BillingDisabledState.tsx` | Instance has no billing config |
| `BillingCheckoutBanner.tsx` | Success/cancel query param alerts |

Reuse `DashboardCard`, `StatCard` where appropriate. Format money with a small helper
`formatMoneyMinorUnits(amount, currency)` in `billing-format.ts`.

## Step 5: Navigation and discoverability

Update when billing is enabled (client checks `fetchBillingStatus` or ui contract flag):

- `frontend/src/lib/navigation.ts`: add under **admin** or **workspace**:

```typescript
{ id: "billing", label: "Billing", href: "/settings/billing", icon: "payments", group: "admin" }
```

- `src/keprix/ui_contract/navigation.py`: matching entry (only if you add server-side
  `billing_enabled` to ui contract; otherwise nav item always visible with disabled
  state on page is acceptable for v1)
- `frontend/src/app/(workspace)/settings/page.tsx`: replace generic duplicate cards with
  one **Billing and subscription** card -> `/settings/billing`
- Optional: TopBar account menu link **Billing** when `enabled`

**Do not** replace marketing `/pricing` entirely in v1; add a note on the billing page
that OSS self-hosters ignore this section. Optional follow-up: dynamic marketing pricing
when `KEPRIX_BILLING_USE_EXAMPLE=true`.

## Step 6: Feature-gate UX hook (minimal)

When API returns 402/403 from `FeatureGateMiddleware`, surface a toast or inline banner:

> This feature requires **{plan}**. [View plans](/settings/billing)

Add a shared helper in `billing-api.ts`:

```typescript
export function isBillingGateError(error: unknown): boolean;
```

Wire in one representative gated surface (e.g. developer API keys page or a single tool
route) as proof; do not blanket-refactor every page.

## Step 7: Env and local dev

Document in page empty state / `docs/features/billing.md` (short):

```bash
KEPRIX_BILLING_ENABLED=true
KEPRIX_BILLING_USE_EXAMPLE=true
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
KEPRIX_INSTANCE_URL=http://localhost:3000
```

Mock mode works without Stripe for account/trial UI; checkout redirect requires Stripe
test keys.

## Step 8: Tests

`tests/frontend/test_billing_workspace.py`:

1. Required files exist (`billing-api.ts`, `settings/billing/page.tsx`, components)
2. Page handles `billing disabled` copy
3. Plan card labels and checkout handler present in source
4. Navigation includes `/settings/billing`
5. Settings hub links to billing page

`tests/billing/test_portal.py` (extend):

6. `GET /api/billing/status` enabled/disabled shapes
7. `portal/account` includes `plans` array when enabled

Manual smoke:

1. Enable example billing config, log in, open `/settings/billing`
2. Start trial on Pro plan, see status update
3. Subscribe redirects to Stripe Checkout (test mode)
4. Return `?checkout=success` shows confirmation
5. Invoice list renders after webhook or test seed
6. Seat invite on Team plan

## Acceptance criteria

- `/settings/billing` loads for signed-in users without console errors
- When billing disabled, friendly message (not infinite 404 retries)
- When billing enabled, current subscription and plan cards render from API
- Checkout and payment-method flows redirect to Stripe and return to billing page
- Cancel at period end + resume work
- Invoices and seats sections work when data exists
- `pnpm build` passes
- Billing tests pass

## Archive checklist

Move to `prompts-archive/` and update `PROMPT-IMPLEMENTATION-AUDIT.md`,
`prompts-archive/README.md`, and `PROMPT-CROSSREF-GUIDE.md`.

## API reference (existing; do not duplicate backend)

| Method | Path |
| --- | --- |
| GET | `/api/billing/portal/account` |
| GET | `/api/billing/portal/invoices` |
| GET | `/api/billing/portal/invoices/{id}` |
| POST | `/api/billing/portal/checkout` |
| POST | `/api/billing/portal/upgrade` |
| POST | `/api/billing/portal/trial` |
| POST | `/api/billing/portal/cancel` |
| POST | `/api/billing/portal/resume` |
| POST | `/api/billing/portal/payment-method` |
| GET | `/api/billing/portal/seats` |
| POST | `/api/billing/portal/seats/invite` |
| DELETE | `/api/billing/portal/seats/{seat_id}` |

Backend package: `src/keprix/billing/`. Config: `config/billing.example.yaml`.
