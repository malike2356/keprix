# Aiva to Keprix map

Aiva is the managed SaaS product on top of Carina. Keprix adopts **platform lessons**, not the Aiva commercial surface.

## Product boundary

| Surface | Aiva (commercial) | Keprix (MIT self-host) |
| --- | --- | --- |
| Licence | Subscription, Aiva Keys | No remote keys |
| Billing | Stripe, plan tiers | None in core |
| Workers UI | Hire AI employees | Agent apps and playbooks |
| Governance | Included Scout dashboards | Optional Scout connector (Prompt 38) |
| Analytics | Hosted aggregates | Self-hosted `/analytics` |
| Branding | Carina / Aiva | Keprix only |

## Feature mapping

| Aiva feature | Source path | Class | Keprix action |
| --- | --- | --- | --- |
| Stripe checkout | `billing/aiva-stripe-checkout.ts` | paid_managed | Stub hook only; no live Stripe in core |
| Plan gates | `billing/aiva-plan-gates.ts` | paid_managed | Local feature flags |
| Hire workers UI | `app/(workspace)/aiva/AivaHireClient.tsx` | paid_managed | Do not port; use agent apps |
| Governance dashboard | `app/(workspace)/aiva/governance/` | scout_enterprise | `/settings/governance` when Scout connected |
| Scout provisioning | `billing/aiva-scout-provisioning.ts` | scout_enterprise | Paid Scout connector enrollment |
| Managed analytics | `analytics/aiva-analytics-router.ts` | paid_managed | Rebuild self-hosted analytics |
| Aiva Keys | `hosted/cloudflare-saas.ts` | unsafe_or_private | Rejected |
| Tenant subscription store | `workers/aiva-subscription-store.ts` | unsafe_or_private | Rejected: customer data |

## Never copy

- Production `.env` from Carina or Aiva
- Customer data or private tenant records
- `keys.carinaai.uk` or Aiva Keys infrastructure
- Stripe live credentials
- In-app Aiva upsell copy on Keprix surfaces

## Rebuild principle

For each Aiva idea marked `public_core` or `public_optional` in the Carina map, write a **rebuild plan** that describes behavior and data boundaries without copying TypeScript implementation verbatim.
