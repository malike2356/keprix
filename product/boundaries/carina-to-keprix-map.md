# Carina to Keprix map

Reference vision: `planning/prompts/00a-product-vision-and-agent-consolidation-map.md`.

| Carina capability | Source path | Class | Keprix target | Rebuild summary |
| --- | --- | --- | --- | --- |
| pgvector RAG | `memory/db.ts` | public_core | Prompt 06 | Self-hosted memory backends, no tenant schema copy |
| Credential vault | `credentials/credential-store.ts` | public_core | Prompt 08 | Local vault; no `keys.carinaai.uk` |
| Workspace | `conversations/` | public_core | Prompt 10 | Documents, notes, calendar under Keprix UI |
| Provider router | `gateway/` | public_core | Prompt 04 | Extend Keprix router with cost lessons |
| Public API | `public-api/` | public_core | Prompt 18 | OpenAPI, traces, health endpoints |
| Skills packs | `skills/pack-manifests.ts` | public_core | Prompt 36 | Hub manifest validation and install |
| Channels | `channels/channel-router.ts` | public_optional | Prompt 11 | Optional connector adapters |
| Research tools | `tools/research/` | public_optional | Prompt 74 | Self-hosted stats and research workspace |
| MCP registry | `mcp/` | public_optional | Prompt 17 | Admin tools and MCP registry |
| Agent loop | `agents/carina.ts` | public_core | Prompt 03 | Keprix agent spine; discipline patterns only |
| Stripe billing | `billing/aiva-stripe-checkout.ts` | paid_managed | none | Do not port managed SaaS billing |
| Plan gates | `billing/aiva-plan-gates.ts` | paid_managed | none | Local flags only; no remote licence |
| Aiva analytics | `analytics/aiva-analytics-router.ts` | paid_managed | Prompt 54 | Self-hosted analytics UI only |
| Scout provisioning | `billing/aiva-scout-provisioning.ts` | scout_enterprise | Prompt 38 | Optional Scout connector; never bundled |
| Aiva Keys | `hosted/cloudflare-saas.ts` | unsafe_or_private | none | Rejected: remote licence server |
| Trust attestation | `security/behavior-proof.test.ts` | unsafe_or_private | none | Rejected: enterprise chain |
| Ops secrets reload | `ops/secrets-reload.ts` | unsafe_or_private | none | Rejected: internal ops only |
| Tenant store | `workers/aiva-subscription-store.ts` | unsafe_or_private | none | Rejected: customer PII |

## Test mapping

| Carina area | Keprix tests |
| --- | --- |
| memory | `tests/memory/` |
| vault | `tests/security/test_vault.py` |
| workspace | `tests/workspace/` |
| API | `tests/api/` |
| hub | `tests/hub/` |
| research | `tests/research/` |
| scout | `tests/scout/` |
| extraction | `tests/extraction/` |

## Documentation mapping

| Topic | Keprix doc |
| --- | --- |
| Brand boundary | `BRAND-BOUNDARY.md`, marketing site validator |
| Developer identity | `docs/developer-identity.md` |
| Hub packs | `docs/hub/README.md` |
| Scout gates | `product/boundaries/enterprise-gates.md` |
| Rejected features | `product/boundaries/rejected-features.md` |
