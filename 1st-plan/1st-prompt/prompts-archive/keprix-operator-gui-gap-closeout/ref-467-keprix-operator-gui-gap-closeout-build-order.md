# Ref 467: Keprix operator GUI gap closeout build order

**Status:** PENDING (ready to build on owner ask)
**Date:** 2026-08-08
**Writing style:** plain ASCII only (no em/en dashes, no emoji).
**Sibling CRM series:** `keprix-agentic-crm-lead-gen/` (429-450 Must, 466 GUI pack, 451-465 Nice)
**Inventory:** `docs/architecture/operator-gui-gap-inventory.md`

## Why this series exists

A full codebase audit found Keprix capabilities that are implemented as FastAPI
routes, libraries, or agent tools but lack (or mislabel) workspace GUI. Soft Wall
core outreach, contacts, and many nav modules already have GUI. The gaps below
are what operators still cannot safely run without curl, Telegram, or guessing
URLs.

This series closes **every** identified gap from that audit. CRM object model and
full `/crm` console remain owned by the sibling 429-466 programme; prompt **481**
is the verification/execution gate so CRM Critical cannot be marked done here
while still missing.

## Binding rules

1. Sync `navigation.py` and `frontend/src/lib/navigation.ts` for every new route.
2. Never label a nav item with a page that implements a different product (Tool
   ACL -> `/admin/tools` is the anti-pattern to fix in 468).
3. Soft Wall for risky writes; reuse Soft Wall approval inbox; deep-link objects.
4. Tenant/workspace isolation on every new page and API.
5. Empty states honest; no fake demo data.
6. Telegram-only or API-only is **not** Must-done for operator safety surfaces.
7. No nested Carina tree; no new Stripe prices; Contabo deploys must leave
   `https://carinaai.uk/` on HTTP 200.
8. Do not duplicate CRM architecture; execute 429-466 when building CRM GUI.

## Gap -> prompt map

| Audit finding | Severity | Prompt(s) |
| --- | --- | --- |
| Tool ACL API, nav lies to mutation tools | Critical | 468 |
| Soft Wall deliverability missing | High | 469 |
| Outbox / dead-letter missing | High | 470 |
| Suppressions GUI incomplete | High | 471 |
| Contactability (found != contactable) | High | 472 |
| Identity merges Soft Wall | High | 473 |
| Kill switches / cadence / budgets | High | 474 |
| List enroll preflight GUI | High | 475 |
| viCal Soft Wall booking SoT | High | 476 |
| Sheet preprocess library, no HTTP/UI | Critical | 477-478 |
| Discovery framework + jobs GUI | Critical | 479-480 |
| CRM `/crm` console | Critical | 481 + sibling 429-466 |
| Fleet API, no GUI | High | 482 |
| Companion pairing API-only | High | 483 |
| Data plane `/api/data`, no FE | High | 484 |
| Jobs `/api/jobs`, no FE | High | 485 |
| ML `/api/ml`, no FE | High | 486 |
| Export `/api/export`, no FE | High | 487 |
| Improvement proposals no review UI | Medium | 488 |
| Code-agent sessions thin GUI | Medium | 489 |
| Typed agents no GUI | Medium | 490 |
| Kernel plugins no GUI | Medium | 491 |
| Interfaces bind no GUI | Medium | 492 |
| Intent schema admin no GUI | Medium | 493 |
| Tool adapters no GUI | Medium | 494 |
| Eval benchmarks API unused in FE | Medium | 495 |
| Personas picker-only | Medium | 496 |
| Nav orphans / Agent OS depth | Medium | 497 |
| Product leads vs Soft Wall leads confusion | Medium | 498 |
| Opportunities vs CRM deals confusion | Medium | 499 |
| Hot-cache / workspace ops API-only | Medium | 500 |
| gui_catalog understates missing_gui | Medium | 501 |
| Docs / self-knowledge lag | Medium | 502 |
| Credential proxy ops CLI-heavy | Medium | 503 |
| Intentional API-only ambiguity | Medium | 504 |
| Tests + sign-off + archive | Must | 505 |

## Execution order

| Prompt | Title | Depends on |
| --- | --- | --- |
| 467 | Overview, gap inventory, architecture lock | none |
| 468 | Tool ACL admin GUI + nav fix | 467 |
| 469 | Soft Wall deliverability dashboard | 467 |
| 470 | Soft Wall outbox / dead-letter GUI | 467 |
| 471 | Suppressions manager GUI | 467 |
| 472 | Contactability decisions GUI | 467, 471 |
| 473 | Identity merge Soft Wall GUI | 467 |
| 474 | Kill switches, cadence, budgets settings | 469 |
| 475 | List enroll + preflight GUI | 470, 471, 472, 474 |
| 476 | viCal Soft Wall booking SoT | 467 |
| 477 | Sheet preprocess HTTP API + Soft Wall | 467 |
| 478 | Sheet preprocess workspace GUI | 477 |
| 479 | Discovery framework + job runner | 467 |
| 480 | Discovery run form + jobs GUI | 479, 472, 473 |
| 481 | CRM console sibling gate (429-466) | sibling CRM + 475-480 preferred |
| 482 | Enterprise fleet admin GUI | 467 |
| 483 | Mobile companion pairing GUI | 467 |
| 484 | Data plane datasets GUI | 467 |
| 485 | Jobs queue GUI | 484 or 467 |
| 486 | ML workspace GUI | 484 |
| 487 | Document export GUI | 467 |
| 488 | Improvement proposal review GUI | 467 |
| 489 | Code-agent sessions GUI | 467 |
| 490 | Typed agents inventory GUI | 467 |
| 491 | Kernel plugins admin GUI | 467 |
| 492 | Interfaces bind/dispatch GUI | 467 |
| 493 | Intent schema admin GUI | 467 |
| 494 | Tool adapters registry GUI | 467 |
| 495 | Eval benchmarks GUI | 467 |
| 496 | Personas operator inventory GUI | 467 |
| 497 | Nav orphans + Agent OS IA | 467 |
| 498 | Product vs Soft Wall leads clarity | 467 |
| 499 | Opportunities vs CRM clarity | 467 |
| 500 | Hot-cache / workspace ops GUI | 467 |
| 501 | gui_catalog + module inventory honesty | 468-500 as landed |
| 502 | Docs, runbooks, self-knowledge | 501 |
| 503 | Credential proxy ops GUI polish | 467 |
| 504 | Intentional API-only register | 467 |
| 505 | Tests, cutover, sign-off, archive | all prior + 481 |

## Build waves (parallel OK inside wave)

1. **Lock + security:** 467-468
2. **Soft Wall safety:** 469-476
3. **Sheet + discovery + CRM gate:** 477-481 (CRM may run as sibling track)
4. **Enterprise / mobile / data:** 482-487
5. **Platform depth:** 488-496
6. **Findability / clarity / ops:** 497-500, 503
7. **Honesty + docs + register:** 501-502, 504
8. **Sign-off:** 505

## Definition of done (series)

- [ ] Every Critical and High audit row has a shipped GUI path or owner block note
- [ ] Tool ACL nav fixed and functional
- [ ] Soft Wall safety pages operable
- [ ] Sheet + discovery operable
- [ ] CRM console READY via 481/466 or owner-blocked
- [ ] Fleet, companion, data plane, jobs, ML, export operable
- [ ] Medium platform/admin surfaces shipped
- [ ] Nav orphans and leads/opportunities clarity fixed
- [ ] gui_catalog honest; intentional non-GUI register committed
- [ ] Sign-off READY (or partial with owner note); prompts archived

## Prompt files

Under `1st-plan/1st-prompt/pending-prompts/keprix-operator-gui-gap-closeout/`:

- `467-505-README.md`
- `ref-467-keprix-operator-gui-gap-closeout-build-order.md` (this file)
- `467-505-00` through `467-505-38` (prompts 467-505)

## Related

- CRM: `../keprix-agentic-crm-lead-gen/`
- DATA ops archive: `../../prompts-archive/data-ops-surfaces-upgrade.md`
- Soft Wall archive: `aiva-migration/K02-outreach-automation.md` (historical)
