# Prompt: Adopt Managed AI Credit Wallet For Keprix

## Goal

Add a spend-safe managed AI wallet for hosted Keprix while keeping Community Edition and self-hosted users BYOK-first.

## Source Research

Reference only:

- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/src/lib/aiWallet.js`
- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/src/lib/aiCredits.js`
- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/src/lib/planEnforcement.js`
- `/opt/lampp/htdocs/verlox/keprix/1st-plan/competitor-research/00-agents-to-adopt/myapi-open/docs/STRIPE_OVERAGE_SETUP.md`

Do not copy AGPL code. Reimplement the behavior.

## Product Context

Keprix is a self-hosted Agent OS that writes its own tools. The commercial hosted layer can provide managed tokens, but open-source and self-hosted users should be able to bring their own model keys.

## Required Behavior

- Community and self-hosted mode: BYOK is the default.
- Hosted/pro mode: managed token wallet is available and visibly metered.
- Trial mode: fixed credit balance with strict caps.
- Credit ledger records grants, debits, purchases, refunds, expiries, and admin adjustments.
- Every managed LLM call, self-coding action, mutation run, and generated-tool planning call is routed through wallet enforcement.
- Unknown model prices use a conservative fallback so Keprix does not undercharge.
- BYOK calls do not debit the managed wallet.
- Trial exhaustion offers BYOK or paid managed tokens, not a hard product lockout.
- Plan and workspace decisions are resolved server-side, never trusted from request body or query.

## Pricing And Stripe Rules

- Use `/opt/lampp/htdocs/verlox/.access/.stripe-credentials-and-price-id.md` as the only Stripe source.
- Do not create new Stripe prices.
- Use `price_1Tri9T2WMXleLh8eA6gCXHbk` only for the voluntary one-off Keprix Community donation.
- Never gate Community Edition on the donation.
- Never paste Stripe secrets into docs, logs, tests, UI, or chat.

## Implementation Targets To Inspect

- `src`
- `web`
- `memory`
- `config/billing.yaml`
- `docs/features/billing.md`
- `docs/features/llm-usage.md`
- Existing provider routing, workspace, billing, and usage modules.

## Implementation Steps

1. Locate all LLM call paths, including chat, RAG, tool synthesis, mutation, repo editing, tests, and automation.
2. Define a Keprix managed-credit ledger model.
3. Add plan and edition policy for community, self-hosted, hosted trial, starter, and pro.
4. Add managed-call enforcement before provider requests.
5. Add BYOK fallback path and clear UI state.
6. Add admin and user visibility into balance and usage.
7. Update docs so self-hosters understand BYOK and hosted users understand managed tokens.

## Tests

- Managed calls debit the wallet.
- BYOK calls do not debit the wallet.
- Trial caps prevent cost overrun.
- Unknown model pricing cannot undercharge.
- Workspace ID spoofing cannot bypass plan enforcement.

## Done Criteria

- Hosted Keprix cannot lose unbounded model money.
- Self-hosted users can keep using BYOK.
- Trial expiry keeps the user in product.
- Billing config only references existing Stripe prices.
- No AGPL code is copied.
