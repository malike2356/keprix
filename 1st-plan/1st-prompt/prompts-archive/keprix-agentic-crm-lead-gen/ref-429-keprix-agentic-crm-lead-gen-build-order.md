# Ref 429: Keprix agentic CRM + lead-gen + outreach funnel

**Series:** 429-466 core, 506-515 visual Must, 451-465 Nice  
**Status: COMPLETED 2026-08-08** (programme archived; operator enters keys at `/crm/settings#connections`)
**Date:** 2026-08-08  
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

**Binding supplement:** `ref-429-programme-hardening-review.md`. Every prompt
in this series must apply its operating, provenance, compliance, deliverability,
idempotency, human takeover, and sign-off requirements.

## Goal

Ship a **hand-off business workflow** inside Keprix where the agent can:

1. Discover leads from domain-specific sources (Companies House, web, social APIs, property portals, health/social directories, user uploads).
2. Enrich and normalise them into a workspace CRM (accounts, leads, contacts, deals, activities).
3. Present lists/sheets for human **review, CRUD, Soft Wall approval**.
4. Execute multi-channel outreach (email first; Telegram and others as adapters) with Mailchimp-like sequences and Go High Level-like nurture.
5. Track replies/engagement, promote stages (lead -> contact -> customer -> paying), book via viCal when qualified.
6. Answer questions about the data, glean intelligence, and take R/W actions under human gates.
7. Be driven from **all channels**, especially Telegram, with slash/chat prompts.

This is **domain-agnostic** (not property-only). Vertical packs supply source adapters and column schemas; the core CRM and spreadsheet preprocessor stay generic.

## Why now

Users ask for full agentic CRM / lead gen. Keprix already has adjacent pieces that must be **glued**, not rebuilt:

| Existing | Path / note |
| --- | --- |
| Soft Wall outreach | `src/keprix/outreach/` (campaigns, sequences, leads, replies, pipeline, approvals) |
| Contacts | `src/keprix/contacts/` |
| Companies House | `integrations/companies_house/` |
| Opportunity / pain mining | `src/keprix/opportunity/` (product research; not per-lead CRM) |
| Analytics tabular import | `analytics/file_import.py`, `data_plane/tabular_import.py` |
| viCal bookings | `src/keprix/vical/` (not wired to outreach bookings) |
| Telegram gateway | `gateway/platforms/telegram*.py` |
| Carina spreadsheet email worker | `carina/.../workers/spreadsheet-processor/` (property-biased enrichment; port pattern, do not nest Carina) |

## Non-goals

- Nesting or copying Carina tree into Keprix (`carina/verlox/` forbidden).
- Scraping that violates site ToS, robots rules, or UK PECR/GDPR without owner legal review.
- New Stripe catalog prices (use Soft Wall / viCal / billing SoT only when owner asks).
- Replacing Soft Wall with a third-party Mailchimp SaaS dependency.
- Full LinkedIn / Meta / TikTok scrape bots as day-one Must (API + honest stubs first).
- Clinicom Contabo flip (still Carina until owner switch).

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
        +-- CRM core (Account, Lead, Contact, Deal, Activity, List, EnrichmentJob)
        |
        +-- Review UI (/crm, /leads, sheet review) + Soft Wall gates
        |
        +-- Outreach engine (existing Soft Wall sequences + enroll)
        |
        +-- Engagement ingest (replies, opens if available, Telegram reactions)
        |
        +-- Stage machine + viCal book when qualified
        |
        +-- Analytics funnel (extend aiva_analytics / Soft Wall metrics)
```

### Spreadsheet preprocessor (Keprix-native)

Port the **pattern** from Carina `spreadsheet-processor` into Keprix:

- Ingest: upload UI, email-to-workspace, agent tool, CSV from discovery.
- Modes:
  - **User-defined schema:** user marks each column as identity / metric / enrichment target / ignore / PII.
  - **Auto-analyse:** model proposes sheet type + column roles + missing metrics; Soft Wall before apply.
- Domain packs: `tenant_list`, `leads`, `property_data`, `clinic_referrals`, `generic`, plus pack-defined types.
- Output: enriched sheet file **and** optional upsert into CRM objects.
- Never property-only; property is one pack.

### CRM object model (Must)

| Object | Purpose |
| --- | --- |
| Account | Company / org |
| Lead | Pre-qualified or cold target (may lack person contact) |
| Contact | Person with email/phone/telegram/address |
| Deal | Opportunity toward paying customer |
| Activity | Email, call note, Telegram message, scrape job, enrichment |
| List | Named lead/contact set for review and enroll |
| EnrichmentJob | Spreadsheet or batch enrich run |
| ConsentRecord | Lawful basis / opt-in / suppression |

Tenant isolation: every row scoped by workspace/user per `TENANT-ISOLATION.md`.

### Stage machine (Must)

```
discovered -> enriched -> listed -> approved -> enrolled -> contacted
  -> engaged -> qualified -> booked -> customer -> paying
  (also: suppressed, bounced, do_not_contact, lost)
```

Human gates (configurable per workspace):

- Approve discovery list before enrich
- Approve enrich fills before write
- Approve list before enroll
- Approve first outbound
- Approve stage jump to customer/paying
- Approve external scrape jobs

### Channel matrix

| Channel | Role in v1 |
| --- | --- |
| Web workspace | Full CRUD + Soft Wall |
| Telegram | Prompt discovery, approvals, digests, slash |
| Email | Outbound sequences + inbound reply classify |
| viCal public book | Qualified booking CTA |
| Social APIs | Discovery adapters (phased) |

## Must-haves (ship without these = incomplete)

1. Domain-agnostic spreadsheet preprocessor with user column map + AI propose.
2. CRM core store + API + UI list/detail CRUD.
3. Soft Wall on enrich apply, list approve, enroll, first send.
4. Agent tools: search/list/create/update CRM; ask-data Q&A; enroll; log activity.
5. Glue: Companies House (and CSV) -> List -> Soft Wall -> Soft Wall outreach enroll.
6. Reply ingest -> engagement activity -> stage update.
7. viCal deep-link or booking create when stage `qualified`/`booked`.
8. Telegram: slash + natural language to start discovery / approve / digest.
9. Suppression list + PECR/GDPR consent fields (honest UK defaults).
10. Docs + tests + self-knowledge snippets.
11. Vertical **pack interface** (property, health, generic) even if only CH+CSV+generic ship first.
12. Audit log for agent R/W on CRM rows.
13. Field-level provenance and identity resolution with reversible merge suggestions.
14. Contactability policy decision distinct from discovery and enrichment.
15. Transactional outbox, send idempotency, final suppression check, reply pause, and dead-letter handling.
16. Sender-domain readiness, bounce/complaint handling, kill switches, budgets, and human takeover queue.

## Nice-to-haves (P5)

Prompts **451-465** (see `451-465-README.md`). Build after Must dependencies.

1. Open/click tracking (pixel / link wrapper) with privacy toggle. (460)
2. A/B subject lines / template experimentation. (455)
3. LinkedIn / Meta / TikTok official API adapters when credentials exist. (461; stubs in 439)
4. Property portal adapters behind feature flags + legal checklist. (464; pack in 440)
5. Voice notes via Telegram / call notes for activity log. (462)
6. Auto ICP scoring from opportunity engine + account briefs. (463)
7. Multi-language nurture templates. (458)
8. Shared team inboxes / assignment + SLA + collision + comments. (453)
9. WhatsApp Business + SMS after consent infrastructure. (459)
10. Export/import HubSpot, Salesforce, Pipedrive, GHL. (454)
11. Saved versioned ICP definitions and exclusion rules. (452)
12. Data freshness, verification, and conflict dashboard. (457)
13. Licensed enrichment provider adapters (same provenance contract). (456)
14. Visual workflow builder compiling to nurture model. (451)
15. Attribution models sourced / influenced / closed. (465)

## Ultimate (P6, owner ask)

1. Full Go High Level parity (pipelines UI drag-drop, SMS carriers).
2. Marketplace of vertical scrapers (still legal-gated).
3. Predictive send-time and lead scoring ML.
4. Revenue attribution to Stripe customer IDs (existing billing SoT only).

## Standard processes (industry, done better here)

| Process | Usual SaaS | Keprix better path |
| --- | --- | --- |
| List build | Manual CSV upload | Agent discovers + sheet preprocess + Soft Wall |
| Enrichment | Clearbit-style paid APIs | Pack + LLM fill empty cells only + human approve |
| Sequences | Mailchimp/GHL | Soft Wall already native; agent enrolls |
| CRM | Separate HubSpot | Same workspace memory + agent tools |
| Approvals | Manager email | Soft Wall + Telegram digests |
| Booking | Calendly bolt-on | viCal already in Keprix |
| Channels | Email-only or paid SMS | Telegram-native operator + email outbound |
| Compliance | Afterthought | Consent + suppression as first-class objects |

## Important considerations (do not skip)

1. **UK PECR / GDPR:** cold email needs lawful basis; soft opt-in / legitimate interest assessment fields; easy unsubscribe; suppression.
2. **Site ToS:** Zoopla/Rightmove/LinkedIn/Meta/TikTok often prohibit scrape; prefer APIs or licensed data; feature-flag scrapers; document risk.
3. **Rate limits + egress allowlist:** discovery adapters go through existing egress controls.
4. **PII retention:** workspace retention settings; redact in logs.
5. **Hallucinated enrichment:** only fill blank cells; show confidence; Soft Wall default on.
6. **Idempotency:** discovery jobs and enroll must not duplicate leads.
7. **Tenant isolation:** never cross-workspace CRM reads.
8. **Cost:** DeepSeek/LLM enrich batched; budget counters in analytics.
9. **Human fatigue:** digests, not notification spam; batch Soft Wall items.
10. **Honest stubs:** social/property adapters may ship as `status: planned` with tools that return clear "not configured" until keys exist.
11. **No nested Carina:** reimplement processor under `src/keprix/crm/` or `src/keprix/sheet_preprocess/`.
12. **Stripe:** do not create prices; paying stage may link existing customer ids later.
13. **Discovery is not contact permission:** calculate contactability separately for each person, purpose, channel, and jurisdiction.
14. **Deliverability:** verified sender, authentication guidance, warm-up, bounces, complaints, and final suppression checks are hard gates.
15. **Retries:** external actions use idempotency keys, transactional outbox, checkpoints, and dead-letter state.
16. **Human takeover:** replies pause automation; complaints, legal language, negotiation, and low confidence route to a named queue.
17. **Provenance:** store source and evidence per field; model inference is labelled and never presented as verified fact.
18. **Metrics:** optimise qualified pipeline and revenue efficiency while monitoring complaints, unsubscribes, and false enrichment.

## Execution order

| Prompt | Title | Depends on |
| --- | --- | --- |
| 429 | Overview, gap map, architecture lock (COMPLETED 2026-08-08; archived) | none |
| 430 | CRM domain model + store + isolation (COMPLETED 2026-08-08; archived) | 429 |
| 431 | CRM HTTP API + Soft Wall hooks (COMPLETED 2026-08-08; archived) | 430 |
| 432 | CRM workspace UI (lists, detail, CRUD) | (COMPLETED 2026-08-08; archived) 431 |
| 433 | Spreadsheet preprocessor core (classify, schema, fill) | (COMPLETED 2026-08-08; archived) 430 |
| 434 | Spreadsheet UI + email/upload ingest + Soft Wall apply | (COMPLETED 2026-08-08; archived) 433, 431 |
| 435 | Agent tools: CRM R/W + ask-data intelligence | (COMPLETED 2026-08-08; archived) 431 |
| 436 | Discovery adapter framework + job runner | (COMPLETED 2026-08-08; archived) 430 |
| 437 | Companies House + CSV discovery -> List | (COMPLETED 2026-08-08; archived) 436, 432 |
| 438 | Web search / directory discovery adapter | (COMPLETED 2026-08-08; archived) 436 |
| 439 | Social discovery adapters (API-first, honest stubs) | (COMPLETED 2026-08-08; archived) 436 |
| 440 | Property vertical pack (flagged; legal checklist) | (COMPLETED 2026-08-08; archived) 436, 433 |
| 441 | Health / social care vertical pack stub + schema | (COMPLETED 2026-08-08; archived) 436, 433 |
| 442 | List review -> approve -> Soft Wall outreach enroll glue | (COMPLETED 2026-08-08; archived) 432, Soft Wall |
| 443 | Engagement ingest (email replies + Telegram) | (COMPLETED 2026-08-08; archived) 442 |
| 444 | Nurture workflows / stage machine automation | (COMPLETED 2026-08-08; archived) 442, 443 |
| 445 | viCal handoff on qualified/booked | (COMPLETED 2026-08-08; archived) 444 |
| 446 | Telegram slash + channel prompts for full funnel | (COMPLETED 2026-08-08; archived) 435, 442 |
| 447 | Funnel analytics + digests | (COMPLETED 2026-08-08; archived) 443, 444 |
| 448 | Consent, suppression, PECR/GDPR controls | (COMPLETED 2026-08-08; archived) 430, 442 |
| 449 | Domain pack docs + self-knowledge + operator runbook | 440, 441, 447 |
| 466 | CRM operator console + GUI surfacing pack (Must) | 432, 436, 442, 443, 444, 448 |
| 450 | Core tests and visual sign-off handoff (Must) | all core Must including 466 |
| 451 | Narrow visual workflow builder (superseded by Must 508) | 444 |
| 452 | Saved versioned ICP definitions | 430, 436 |
| 453 | Team assignment, SLA inbox, collision, comments | 431, 432, 448 |
| 454 | CRM integrations HubSpot/SF/Pipedrive/GHL | 430, 448 |
| 455 | Template experimentation A/B | 444, 447, 448 |
| 456 | Licensed enrichment providers | 433, 434 |
| 457 | Data freshness / quality dashboard | 430, 447 |
| 458 | Multilingual campaigns | 444, 448 |
| 459 | WhatsApp Business + SMS (after consent) | 448, 444 |
| 460 | Open/click tracking privacy toggle | 443, 447, 448 |
| 461 | Social API adapters production | 439, 436, 448 |
| 462 | Voice notes + call notes | 443, 446, 448 |
| 463 | Auto ICP scoring + account briefs | 452, 435 |
| 464 | Property portal adapters flagged | 440, 436, 448 |
| 465 | Attribution + Nice wave cutover | 447, 445, Nice wave |
| 506 | Visual CRM information architecture (Must) | 429, 431, 432, 466 |
| 507 | Interactive visual pipeline board (Must) | 430-432, 444, 466, 506 |
| 508 | Graphical workflow canvas and builder (Must) | 431, 435, 436, 442-445, 451, 466, 506 |
| 509 | Live workflow execution animation and replay (Must) | 436, 442-445, 508 |
| 510 | Node inspector and workflow debugger (Must) | 435, 508, 509 |
| 511 | CRM metric semantic layer and event model (Must) | 430, 443-448, 506, 507 |
| 512 | Visual analytics dashboards and charts (Must) | 447, 506, 511 |
| 513 | Real-time visual operations and alerts (Must) | 446, 507, 509, 511, 512 |
| 514 | Visual accessibility, responsiveness, and performance (Must) | 506-513 |
| 515 | Visual CRM E2E sign-off and final Must archive | all core Must, 506-514 |

## Definition of done (series)

- [ ] User can upload or email a sheet; map columns or accept AI map; Soft Wall; CRM upsert.
- [ ] User (or Telegram) can ask: find clients in domain X; agent produces List for review.
- [ ] Approved list enrolls Soft Wall sequence; replies update stages.
- [ ] Qualified lead can book via viCal; calendar shows event.
- [ ] Agent answers questions from CRM data with citations to records.
- [ ] Suppression/consent enforced on send.
- [ ] Vertical packs documented; property/social not silently illegal-scrape.
- [ ] Operator can run discover -> Soft Wall list -> enroll -> reply inbox from GUI (466).
- [ ] Jobs, outbox, merges, contactability, deliverability, kill switches viewable in `/crm/*`.
- [ ] Pipeline stages and records are visually represented on a clickable board.
- [ ] Full workflow is visible and editable as a validated, versioned node graph.
- [ ] Live and historical executions animate only from durable run events.
- [ ] Every node is clickable for state, evidence, policy, attempts, cost, and errors.
- [ ] Dashboards expose funnel, pipeline, source, outreach, workflow, revenue, cost, and safety metrics.
- [ ] Charts reconcile through one semantic metric layer and drill into exact records.
- [ ] Visual surfaces pass keyboard, semantic alternative, reduced-motion, mobile, and performance gates.
- [ ] `pytest` suites for crm, sheet_preprocess, discovery; frontend smoke for all Must CRM routes; docs shipped.
- [ ] Prompts archived when complete.

## Prompt files

Under `1st-plan/1st-prompt/prompts-archive/keprix-agentic-crm-lead-gen/`:

- `429-450-README.md` (Must index, includes 466)
- `451-465-README.md` (Nice P5)
- `506-515-README.md` (visual CRM Must sprint)
- `429-450-00` through `429-450-21` (Must prompts 429-450)
- `429-466-22-crm-operator-console-gui-surfacing.md` (Must GUI pack)
- `451-465-01` through `451-465-15` (Nice prompts 451-465)
- `506-515-23` through `506-515-32` (visual Must prompts 506-515)
- `ref-429-keprix-agentic-crm-lead-gen-build-order.md`
- `ref-429-programme-hardening-review.md`

## Related archives / siblings

- Operator GUI gap closeout **467-505**:
  `../keprix-operator-gui-gap-closeout/` (Soft Wall safety, Tool ACL, data plane,
  fleet, companion, platform admin GUIs; CRM gate prompt 481)
- Soft Wall: `aiva-migration/K02-outreach-automation.md`
- Contacts: `12-contact-manager-and-sync.md`
- Opportunity: `84-95`
- viCal: `376-388-*`
- Capability mesh: `389-402-*`
- Carina worker (reference only): `carina/02-backends/workers/spreadsheet-processor/`
