# Agentic CRM gap map and architecture lock (programme 429-450 + 466)

**Status:** ARCHITECTURE LOCKED (prompt 429)  
**Date:** 2026-08-08  
**Build order:** `1st-plan/1st-prompt/pending-prompts/keprix-agentic-crm-lead-gen/ref-429-keprix-agentic-crm-lead-gen-build-order.md`  
**Hardening review (binding):** `1st-plan/1st-prompt/pending-prompts/keprix-agentic-crm-lead-gen/ref-429-programme-hardening-review.md`  
**GUI pack:** `1st-plan/1st-prompt/pending-prompts/keprix-agentic-crm-lead-gen/429-466-22-crm-operator-console-gui-surfacing.md`  
**Sibling operator GUI:** `docs/architecture/operator-gui-gap-inventory.md` (programme 467-505; CRM gate 481)

This document freezes names, packages, stages, Soft Wall gates, pack interface,
GUI IA, non-goals, and legal constraints so prompt **430+** does not re-debate
them. Soft Wall, contacts, and viCal are glued, not rebuilt.

## User story (compressed)

Hand-off business workflow: discover clients from many sources, enrich sheets
(domain-agnostic), review/approve lists, Soft Wall outreach, nurture like GHL,
collect replies, book via viCal, promote to customer/paying. Operable from
Telegram **and** workspace GUI with human gates. API-only or Telegram-only
fails Must.

## Architecture (target)

```
Channels (Telegram, web chat, email inbound, slash)
        |
        v
Agent tools + Soft Wall approvals
        |
        +-- Discovery adapters (CH, web, social API, property, health, CSV/email sheet)
        |
        +-- Spreadsheet preprocessor (schema detect OR user column map -> metrics)
        |
        +-- CRM core (Account, Lead, Contact, Deal, Activity, List, EnrichmentJob, ConsentRecord)
        |
        +-- Review UI (/crm/*) + Soft Wall gates
        |
        +-- Outreach engine (existing Soft Wall sequences + enroll)
        |
        +-- Engagement ingest (replies, opens if available, Telegram reactions)
        |
        +-- Stage machine + viCal book when qualified
        |
        +-- Analytics funnel (extend aiva_analytics / Soft Wall metrics)
```

## Existing building blocks (inventory)

| Area | Path | Status | Gap |
| --- | --- | --- | --- |
| Soft Wall outreach | `src/keprix/outreach/` | SHIPPED | No CRM List enroll glue; no CRM-typed Soft Wall payloads for enrich/merge/kill switch |
| Contacts | `src/keprix/contacts/` | SHIPPED | Person store only; not Account/Lead/Deal/stages; must map, not overwrite silently |
| Companies House | `src/keprix/integrations/companies_house/`, tools | SHIPPED | Research + Soft Wall ingest UI; not discovery adapter -> CRM List |
| Opportunity / pain mining | `src/keprix/opportunity/` | SHIPPED | Product research; not per-lead CRM. Keep separate nav honesty (GUI 499) |
| Analytics tabular import | `analytics/file_import.py`, `data_plane/tabular_import.py` | PARTIAL | Safe propose/apply core also in `sheet_preprocess/`; no CRM UI, Soft Wall apply, or model adapter yet |
| Sheet preprocess baseline | `src/keprix/sheet_preprocess/` | SHIPPED (433 core) | Safe propose/apply, roles, pack registry hook, CRM upsert plan object; UI/Soft Wall apply still 434 |
| viCal bookings | `src/keprix/vical/` | SHIPPED | Not wired to Soft Wall / CRM stage `qualified`/`booked` |
| Telegram gateway | `gateway/platforms/telegram*.py` | SHIPPED | Operator channel; no CRM slash / signed Soft Wall digest yet |
| Carina spreadsheet worker | `carina/02-backends/workers/spreadsheet-processor/` | EXTERNAL | Pattern reference only; never nest Carina into Keprix |
| CRM core | `src/keprix/crm/` | SHIPPED (430) | HTTP API Soft Wall hooks still 431; UI 432/466 |
| Discovery framework | `src/keprix/discovery/` | SHIPPED (436-441) | Packs generic/property/health; social/portal stubs honest |
| Operator console `/crm/*` | frontend | SHIPPED (466) | Full IA routes API-backed; Soft Wall panels; flag gates nav |

## Frozen object model (Must names)

Use these PascalCase types in store, API, tools, and docs. Do not rename without
owner ask.

| Object | Purpose |
| --- | --- |
| Account | Company / org |
| Lead | Pre-qualified or cold target (may lack person contact) |
| Contact | Person with email/phone/telegram/address |
| Deal | Opportunity toward paying customer |
| Activity | Email, call note, Telegram message, scrape job, enrichment |
| List | Named lead/contact set for review and enroll |
| ListMembership | Membership of a Contact or Lead in a List |
| EnrichmentJob | Spreadsheet or batch enrich run |
| ConsentRecord | Lawful basis / opt-in / suppression evidence |
| SuppressionEntry | Channel/address block that always wins over consent |

Supporting types for later GUI (prefer first-class, not opaque blobs):  
`DiscoveryJob`, `OutboxRecord`, `MergeSuggestion`, `ContactabilityDecision`,
`SenderReadiness`, `KillSwitchState`, field-level `Provenance`, `SourceRecord`.

Tenant isolation: every durable row scoped by `workspace_id` (central
repository filter; callers cannot opt out). Soft-delete window for bulk
destructive changes.

## Frozen stage machine

Forward path:

```
discovered -> enriched -> listed -> approved -> enrolled -> contacted
  -> engaged -> qualified -> booked -> customer -> paying
```

Terminal / side states (also first-class):

```
suppressed, bounced, do_not_contact, lost
```

Rules:

- Stage suggestions and communication state are separate (reply may pause
  sequence without promoting a Deal).
- `customer` and `paying` require verified business events (or manually
  verified deal outcome with actor/evidence), not model sentiment.
- Stripe: do not create prices; `paying` may link existing customer ids later
  only from Soft Wall / billing SoT.

## Frozen Soft Wall gate list

Configurable per workspace; defaults on for Must. Reuse Soft Wall
(`outreach_approvals` / Soft Wall extension payloads); do not invent a parallel
approval system.

| Gate | When |
| --- | --- |
| Approve discovery list before enrich | List materialised from discovery |
| Approve enrich fills before write | Sheet/CRM apply of model fills |
| Approve list before enroll | Before Soft Wall sequence enroll |
| Approve first outbound | First send per campaign/recipient policy |
| Approve stage jump to customer/paying | Promotion to those stages |
| Approve external scrape jobs | Any flagged scraper / portal adapter |
| Approve identity merge | MergeSuggestion apply |
| Approve kill-switch off | Re-enabling sends after pause |
| Approve contactability allow (bulk) | When policy says needs_review |

Telegram Soft Wall actions require linked account, short-lived signed token,
single use, visible scope, expiry.

## Package paths (agreed)

| Package | Role |
| --- | --- |
| `src/keprix/crm/` | Domain model, store, identity resolution, outbox primitives, consent/suppression models |
| `src/keprix/sheet_preprocess/` | Domain-agnostic spreadsheet classify/map/propose/apply (extend existing) |
| `src/keprix/discovery/` | Adapter framework, job runner, CH/CSV/web/social adapters |
| `src/keprix/outreach/` | Soft Wall sequences, enroll, replies (glue only; no fork) |
| `src/keprix/contacts/` | Existing person store; CRM Contact maps/syncs with conflict UI |
| `src/keprix/vical/` | Booking create / deep-link on qualified/booked |
| `frontend` `/crm/*` | Operator console (IA below; full screens in 466) |
| `docs/features/crm-packs/` | Vertical pack docs (449) |
| `docs/self-knowledge/parity/` | Self-knowledge outlines and later snippets |

Domain pack code lives under `src/keprix/discovery/packs/` (or
`src/keprix/crm/packs/` for schema-only). Prefer discovery packs for source
adapters; CRM packs for column schemas and stage defaults.

## Vertical pack interface

Each pack ships:

1. **Manifest** (`pack.yaml` or equivalent): `id`, `display_name`,
   `source_category`, licence/terms reference, allowed fields, permitted
   purposes, rate limits, geographic scope, retention, `outreach_allowed`,
   feature flags, health endpoint contract.
2. **Adapters:** implement discovery adapter protocol (fetch, checkpoint,
   evidence, cost estimate, degrade to `not_configured`).
3. **Sheet schemas:** named sheet types (`tenant_list`, `leads`,
   `property_data`, `clinic_referrals`, `generic`, plus pack-defined).
4. **Column roles:** identity / metric / enrichment target / ignore / PII.
5. **Contactability defaults:** organisation vs person; health packs default to
   organisation and professional contacts only (no patient/care-recipient lead
   gen).

Must ship first: Companies House + CSV + `generic`. Property and health packs
may be stubs with honest `status: planned` until legal/flagged paths exist.

## Must GUI routes (IA)

Every Soft Wall-gated Must capability needs a workspace route or Soft Wall
panel. Telegram-only fails Must. Full screen detail: prompt **466**. Foundation
CRUD starts in **432**.

**Status 2026-08-08 (prompts 449/466/450):** All Must routes exist under
`frontend/.../crm/` and are API-backed (no `CrmStubPage`). Soft Wall safety
routes use CRM APIs (merges, outbox, deliverability, contactability,
suppressions, settings). Discover/jobs/enrich/inbox/workflows live. Feature
flag `crm_funnel` / `KEPRIX_CRM_FUNNEL` gates nav ids `crm`, `crm-enrich`,
`crm-discover`, `crm-jobs`. Docs and self-knowledge snippets shipped (449).
Sign-off: `docs/architecture/agentic-crm-signoff.md`. Visual Must-thin sprint
506-515 shipped (see `docs/architecture/visual-crm-signoff.md`); prompts remain
pending for archive until owner allows.

| Route | Purpose | Owner prompts |
| --- | --- | --- |
| `/crm` | Overview: funnel KPIs, Soft Wall pending, kill-switch | 432, 466 |
| `/crm/pipeline` | Visual Kanban board + inspector | 507 |
| `/crm/accounts`, `/crm/accounts/[id]` | Account CRUD + provenance | 432, 466 |
| `/crm/leads`, `/crm/leads/[id]` | Lead CRUD | 432, 466 |
| `/crm/contacts`, `/crm/contacts/[id]` | Contact CRUD + consent | 432, 466 |
| `/crm/deals`, `/crm/deals/[id]` | Deal CRUD + stage | 432, 466 |
| `/crm/lists`, `/crm/lists/[id]` | Lists + enroll | 432, 442, 466 |
| `/crm/discover` | Discovery run form | 436, 437, 466 |
| `/crm/jobs` | Discovery + enrich job history | 436, 466 |
| `/crm/enrich` | Sheet preprocess | 434 |
| `/crm/inbox` | Engagement / replies / takeover | 443, 466 |
| `/crm/workflows`, `/crm/workflows/[id]` | List + canvas (508; satisfies Nice 451 scope) | 444, 466, 508 |
| `/crm/runs/[id]` | Live/replay execution animation | 509 |
| `/crm/analytics` | Semantic dashboards | 511, 512 |
| `/crm/ops` | Real-time ops centre (polling Must-thin) | 513 |
| `/crm/deliverability` | Sender readiness, bounces, budgets | 442, 448, 466 |
| `/crm/outbox` | Outbox, dead letters, idempotent send | 442, 466 |
| `/crm/merges` | Identity merge Soft Wall | 430, 466 |
| `/crm/contactability` | Person x channel x purpose decisions | 430, 448, 466 |
| `/crm/suppressions` | Suppression manager | 448, 466 |
| `/crm/settings` | Kill switches, caps, pack flags, budgets | 466 |

Feature flag: `KEPRIX_CRM_FUNNEL` hides nav when off. Sync
`ui_contract/navigation.py` and `frontend/src/lib/navigation.ts`.

## Gaps to close (Must)

1. CRM object model + store + isolation + provenance + merges (430) DONE
2. CRM HTTP API + Soft Wall hooks (431) DONE
3. CRM workspace UI foundation (432) DONE
4. Domain-agnostic sheet preprocess extend + UI Soft Wall apply (433-434) DONE
5. Agent tools: CRM R/W + ask-data (435) DONE
6. Discovery framework + CH/CSV/web; social API-first stubs (436-439) DONE
7. Vertical packs property/health (flagged / stub) (440-441) DONE
8. List Soft Wall -> Soft Wall enroll glue (442) DONE
9. Engagement ingest + nurture stage machine (443-444) DONE
10. viCal handoff (445) DONE
11. Telegram funnel prompts + signed Soft Wall (446) DONE
12. Funnel analytics + digests (447) DONE
13. Consent / suppression / PECR-GDPR controls (448) DONE
14. Docs, self-knowledge, runbook (449) DONE
15. Operator console pack (466) DONE
16. Tests, cutover, sign-off (450; requires 466 GUI gate) DONE (core; see sign-off)
17. Visual CRM sprint 506-515 Must-thin SHIPPED (archive deferred; see visual-crm-signoff.md)

## Self-knowledge (449 shipped)

| Doc id | Topics |
| --- | --- |
| `parity/agentic-crm-outline.md` | Programme status |
| `parity/agentic-crm-objects.md` | Object names, stages, Soft Wall gates |
| `parity/agentic-crm-routes.md` | `/crm/*` sitemap matching 466 |
| `parity/agentic-crm-tools.md` | Agent tools including crm enroll |
| `parity/agentic-crm-packs.md` | Pack ids, enabled vs stub adapters |
| `parity/agentic-crm-compliance.md` | Consent, suppression, PECR/GDPR |
| Feature doc | `docs/features/agentic-crm.md` |
| Pack docs | `docs/features/crm-packs/{generic,property,health_social}.md` |

Index smoke: `keprix memory search-self "crm enroll"` after reindex.

## Sign-off

Filled by prompt 450 in `docs/architecture/agentic-crm-signoff.md`. READY
requires 466 GUI gate. Final Must archival waits for visual prompt 515 when
that sprint is in scope. Fail closed if any Soft Wall-gated Must lacks a GUI path.

## Non-goals (explicit)

- Nesting or copying Carina tree into Keprix (`carina/verlox/` forbidden).
- Scraping that violates site ToS, robots rules, or UK PECR/GDPR without owner
  legal review.
- New Stripe catalog prices (use Soft Wall / viCal / billing SoT only when
  owner asks).
- Replacing Soft Wall with a third-party Mailchimp SaaS dependency.
- Full LinkedIn / Meta / TikTok scrape bots as day-one Must (API + honest stubs
  first).
- Clinicom Contabo flip (still Carina until owner switch).
- Treating opportunity engine as the sales CRM.
- Silent overwrite of `contacts/` from CRM Contact without conflict UI.
- Parallel approval system beside Soft Wall.
- Fully autonomous negotiation or closing.
- Open/click tracking as Must (Nice 460; privacy-sensitive).

## Legal / safety constraints (series-wide)

- **UK PECR / GDPR:** cold email needs lawful basis; soft opt-in / legitimate
  interest assessment fields; easy unsubscribe; suppression always wins.
- **Discovery is not contact permission:** ContactabilityDecision is separate
  per person, channel, purpose, jurisdiction.
- **Site ToS:** Zoopla/Rightmove/LinkedIn/Meta/TikTok often prohibit scrape;
  prefer APIs or licensed data; feature-flag scrapers; document risk.
- Empty-cell-only enrichment; confidence + Soft Wall before apply; never present
  model inference as verified fact.
- Rate limits + egress allowlist for discovery adapters.
- PII retention / redaction in logs; DSAR/erasure runbooks in 448/449/450.
- Idempotency: discovery, enroll, send, reply, booking must not duplicate.
- Deliverability: sender readiness, final suppression check, bounce/complaint
  handling, kill switches, budgets, human takeover queue.
- Binding detail: `ref-429-programme-hardening-review.md`.

## Channel matrix (v1)

| Channel | Role |
| --- | --- |
| Web workspace | Full CRUD + Soft Wall (Must) |
| Telegram | Prompt discovery, Soft Wall digests, slash (Must; not sole surface) |
| Email | Outbound sequences + inbound reply classify |
| viCal public book | Qualified booking CTA |
| Social APIs | Discovery adapters (phased; stubs OK) |

## Sign-off pointer

See `docs/architecture/agentic-crm-signoff.md` (prompt 450). Visual sprint
506-515 owns final Must archival when that series is in the active queue.
