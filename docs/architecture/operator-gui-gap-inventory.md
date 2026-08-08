# Operator GUI gap inventory (programme 467-505)

**Status:** PLAN LOCKED (implementation in progress; 467 done)
**Date:** 2026-08-08
**Build order:** `1st-plan/1st-prompt/pending-prompts/keprix-operator-gui-gap-closeout/ref-467-keprix-operator-gui-gap-closeout-build-order.md`
**Series README:** `1st-plan/1st-prompt/pending-prompts/keprix-operator-gui-gap-closeout/467-505-README.md`
**Sibling CRM:** `docs/architecture/agentic-crm-gap-map.md` + prompts 429-466

## Method

Compared ~211 mounted FastAPI routers under `src/keprix/` against ~205 Next.js
`page.tsx` routes and the nav contract (`navigation.py` / `navigation.ts`).
Frontend string search found **zero** clients for `/api/data`, `/api/ml`,
`/api/jobs`, `/api/export`, `/api/fleet`, `/api/companion`, `/api/security/acl`.

## Frozen route IA (do not invent parallel paths)

| Surface | Routes / tabs | Owner prompts |
| --- | --- | --- |
| Tool ACL | `/admin/tool-acl` | 468 |
| Soft Wall safety | `/outreach/deliverability`, `/outreach/outbox`, `/outreach/suppressions`, `/outreach/merges`, `/outreach/contactability`, `/outreach/settings` | 469-474 |
| Soft Wall enroll + viCal | `/outreach` list enroll + booking SoT | 475-476 |
| Sheet + discovery | `/crm/enrich`, `/crm/discover`, `/crm/jobs` (or Soft Wall aliases until CRM) | 477-480 |
| CRM console | full `/crm/*` | 481 + sibling 429-466 |
| Fleet / companion | `/admin/fleet`, `/admin/companion` | 482-483 |
| Data plane / jobs / ML / export | `/data?tab=datasets|jobs|ml|export` | 484-487 |
| Platform depth | `/admin/*` and Agent Studio as specified | 488-496 |
| Nav / clarity | nav sync + labels | 497-500 |
| Catalog / docs / sign-off | gui_catalog, docs, proxy ops, intentional register | 501-505 |

## Soft Wall reuse policy

- Do not fork a second outreach approval inbox.
- Deep-link Soft Wall approvals with mesh / CRM / outreach ids.
- Soft Wall safety pages (469-476) may ship before full CRM and are reused as CRM deep links.

## Nav contract rules

1. Sync `src/keprix/ui_contract/navigation.py` and `frontend/src/lib/navigation.ts` on every new route.
2. Never label a nav item with a destination that implements a different product (Tool ACL pointing at mutation tools is the anti-pattern).
3. Tenant/workspace isolation on every new page (workspace-scoped fetches only).
4. Empty states honest; no fake demo data.
5. Telegram-only or API-only is **not** Must-done for operator safety surfaces.

## Feature flags / edition gates

| Surface | Gate |
| --- | --- |
| Fleet admin (`/admin/fleet`) | Enterprise / edition gate (prompt 482) |
| Soft Wall safety pages | Reuse existing Soft Wall / research flags where already gated |
| Tool ACL, companion, data plane tabs, platform admin | Admin group; no extra progressive flag required |
| CRM `/crm/*` | Sibling programme; not gated by this series alone |

Flags remain progressive UX switches (`FLAG_NAV_GATES`), not a full module map. Wider catalog: `/settings/modules`, `/developer/module-inventory`.

## Explicit non-goals

- No nested Carina tree (`carina/verlox/` forbidden).
- No new Stripe prices.
- Contabo deploys must leave `https://carinaai.uk/` on HTTP 200.
- This series does **not** replace CRM 429-466. Prompt 481 fails if CRM Must GUI is missing.

## Critical (needs operator GUI)

| Capability | Backend | GUI today | Prompt |
| --- | --- | --- | --- |
| Tool ACL + resource grants | `/api/security/acl/*` | `/admin/tool-acl` (prompt 468) | 468 |
| Sheet preprocess | `sheet_preprocess/` + `/api/crm/sheets` | `/crm/enrich` | 477-478 |
| Discovery framework + jobs | `/api/crm/discovery*` | `/crm/discover`, `/crm/jobs` | 479-480 |
| CRM operator console `/crm/*` | CRM API + Soft Wall glue | `/crm/*` READY (gate 481) | 481 + 429-466 |

## High (shipped API; needs GUI)

| Capability | Backend | GUI today | Prompt |
| --- | --- | --- | --- |
| Soft Wall deliverability | Soft Wall email/settings partial | `/outreach/deliverability` | 469 |
| Outbox / dead letters | send path; not operator-visible | `/outreach/outbox` | 470 |
| Suppressions | compliance models planned / Soft Wall | `/outreach/suppressions` | 471 |
| Contactability | policy must be separate from discovery | `/outreach/contactability` | 472 |
| Identity merges | store requirements in CRM hardening | `/outreach/merges` | 473 |
| Kill switches / budgets | send path requirements | `/outreach/settings` | 474 |
| List enroll preflight | Soft Wall + CRM 442 | `/outreach/lists` Soft Wall enroll modal | 475 |
| viCal Soft Wall booking SoT | both APIs exist; not wired | viCal confirm handoff + Soft Wall bookings mesh | 476 |
| Fleet | `/api/fleet` | `/admin/fleet` | 482 |
| Companion pairing | `/api/companion` | `/admin/companion` | 483 |
| Data plane | `/api/data` | `/data?tab=datasets` | 484 |
| Jobs queue | `/api/jobs` | `/data?tab=jobs` | 485 |
| ML workspace | `/api/ml` | `/data?tab=ml` | 486 |
| Document export | `/api/export` | `/data?tab=export` | 487 |

## Medium (needs GUI or findability)

| Capability | Backend | GUI today | Prompt |
| --- | --- | --- | --- |
| Improvement proposals | `/api/improvement` | `/agent-os/improvements` | 488 |
| Code-agent sessions | `/api/code-agent` | `/admin/code-agent` | 489 |
| Typed agents | `/api/typed-agents` | `/admin/typed-agents` | 490 |
| Kernel plugins | `/api/kernel` | `/admin/kernel` | 491 |
| Interfaces | `/api/interfaces` | `/admin/interfaces` | 492 |
| Intent schema | `/api/intent` | `/admin/intent` | 493 |
| Tool adapters | `/api/tools/adapters` | `/admin/tool-adapters` | 494 |
| Eval benchmarks | `/api/evals/benchmarks` | `/evals` benchmarks section | 495 |
| Personas inventory | `/api/personas` | `/admin/personas` | 496 |
| Nav orphans / Agent OS depth | pages exist | Linked via nav + Agent OS more | 497 |
| Product vs Soft Wall leads | `/leads` + `/outreach/leads` | Product signups vs Outreach leads | 498 |
| Opportunities vs CRM | `/opportunities` | Research opportunities + CRM deals link | 499 |
| Hot-cache / workspace ops | workspace APIs | `/admin/workspace-ops` | 500 |
| gui_catalog honesty | `upgrade/gui_catalog.py` | Series surfaces mapped | 501 |
| Docs / self-knowledge | glossary + signoff | Updated | 502 |
| Credential proxy ops | `/api/admin/proxy` | Credentials ProxyOpsPanel | 503 |

## Intentional non-GUI register

Owner-approved surfaces that must **not** be tracked as `missing_gui`. Catalog
marks these `cli_api` or `integration`.

| Surface | Classification | Rationale (owner) |
| --- | --- | --- |
| Slash commands / TUI | `cli_api` | Terminal-first operator UX |
| Public `/v1` and OpenAI-compat bridges | `integration` | External clients, not workspace GUI |
| Carina / Scout external bridges | `integration` | Cross-product control planes |
| Auth handoff / OIDC callbacks | `integration` | Browser redirect flows |
| Health / metrics scrape endpoints | `cli_api` | Infra monitoring |
| CLI auto-config | `cli_api` | Installer and headless setup |
| Email-shield alias | covered by Channel Shield GUI | Alias only |
| Pure infra heartbeats / worker claim tokens | `cli_api` | Worker protocol |

No Critical/High Must item from this series may move here without an owner note
in this table.

## Already well surfaced (not in this series as builds)

Soft Wall core outreach (`/outreach/*`), contacts, calendar/viCal hubs, Channel
Shield, Review Gateway, vault, playbooks, billing, RAG, research, browser, cron,
MCP, mutation review, brain/memory, Aiva analytics/escalations.

## Sign-off

Filled by prompt 505 in `docs/architecture/operator-gui-gap-signoff.md`.
