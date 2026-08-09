# Agentic CRM and lead-gen funnel

Keprix agentic CRM is a review-first revenue workflow: discover, enrich, Soft Wall
approve, enroll, nurture, engage, book via viCal, then promote to customer/paying.
Operators run it from the workspace GUI under `/crm/*`. Telegram digests and slash
commands are helpers, not the only surface.

Architecture lock: `docs/architecture/agentic-crm-gap-map.md`  
Compliance detail: `docs/features/crm-compliance.md`  
Pack docs: `docs/features/crm-packs/`  
Operator help: [CRM troubleshooting](../troubleshooting/agentic-crm.md)

## What is automated vs Soft Wall

| Step | Automated | Needs Soft Wall / human |
| --- | --- | --- |
| Discovery fetch | Adapter run, candidate draft | Scrape-flagged adapters; list materialise before enrich |
| Sheet propose | Classify, map, empty-cell fill proposals | Apply writes / CRM upsert |
| List enroll | Preflight counts and deny reasons | Approve list before Soft Wall sequence enroll |
| First outbound | Scheduling when eligible | First send per campaign / recipient policy |
| Identity merge | Fuzzy suggestions only | Apply merge (consent never auto-unioned) |
| Kill switch off | Pause is immediate | Resume requires Soft Wall |
| Stage to customer/paying | Suggestions in inbox | Promotion with evidence |
| Contactability allow (bulk) | Deny blocks enroll UI | Allow when policy says needs_review |

Marketing honesty: Keprix does not silently spam. Discovery is not contact
permission. Suppression always wins.

## Feature flag

Env / flag id: `KEPRIX_CRM_FUNNEL` / `crm_funnel` (default on).

When off, sidebar hides CRM overview, Sheet enrich, Discover, and CRM jobs for
non-admin roles. Direct `/crm/*` URLs still exist for admins and deep links;
operators should treat the flag as the progressive UX gate.

Kill switches live under `/crm/settings` (workspace pause is immediate; resume is
Soft Wall gated).

## Operator console sitemap (Must routes)

| Route | Purpose |
| --- | --- |
| `/crm` | Funnel KPIs, Soft Wall pending panel, kill-switch hints, surface links |
| `/crm/accounts`, `/crm/accounts/[id]` | Account CRUD + provenance |
| `/crm/leads`, `/crm/leads/[id]` | Lead CRUD |
| `/crm/contacts`, `/crm/contacts/[id]` | Contact CRUD + consent |
| `/crm/deals`, `/crm/deals/[id]` | Deal CRUD + stage |
| `/crm/lists`, `/crm/lists/[id]` | Lists, members, Soft Wall enroll |
| `/crm/discover` | Discovery run form |
| `/crm/jobs`, `/crm/jobs/[id]` | Discovery + enrich job history; cancel, materialize, retry |
| `/crm/enrich` | Sheet preprocess propose / Soft Wall apply |
| `/crm/inbox` | Replies, stage suggestions, takeover, complaints |
| `/crm/workflows` | Nurture list: view, pause, activate, Soft Wall sequence link |
| `/crm/deliverability` | Sender readiness, bounce/complaint rates, budgets |
| `/crm/outbox` | Outbox, dead letters, Soft Wall-aware retry |
| `/crm/merges` | Identity merge suggestions Soft Wall |
| `/crm/contactability` | Person x channel x purpose decisions |
| `/crm/suppressions` | Suppression manager |
| `/crm/settings` | Kill switches, cadence caps, pack / policy notes |

Tab nav: `CrmTabNav` on every CRM page. Soft Wall inbox also deep-links CRM
objects with `?approval=` where approvals exist.

## Operator runbook (GUI paths)

1. **Discover** - `/crm/discover`: pick adapter (Companies House, CSV, web, pack),
   run job. Watch `/crm/jobs`. Soft Wall materialize creates a draft List.
2. **Enrich** - `/crm/enrich`: upload sheet, propose, Soft Wall apply empty cells
   only. Optional CRM upsert into accounts/leads/contacts.
3. **Soft Wall list review** - `/crm/lists/[id]`: edit members, run enroll
   preflight. Contactability deny and suppressions block with reasons and links
   to `/crm/contactability` / `/crm/suppressions`.
4. **Enroll** - same list page: choose Soft Wall sequence, Soft Wall enroll.
   Pending items appear on `/crm` Soft Wall panel and can be approved there.
5. **Nurture** - `/crm/workflows`: pause / activate sequences; deep-link Soft Wall
   for step edit (full canvas is Nice 451).
6. **Engage** - `/crm/inbox`: claim replies and takeover; pause automation; Soft
   Wall stage suggestions. Complaints and unsubs create suppressions.
7. **Deliverability / outbox** - `/crm/deliverability` checklist before cold send;
   `/crm/outbox` for failed and dead-letter rows (retry Soft Wall gated; no silent
   double-send).
8. **Book** - qualified leads: Soft Wall / tools offer viCal booking; stage moves
   toward booked then customer/paying with Soft Wall.
9. **Ops** - `/crm/settings` kill switch; `/crm/merges` for identity Soft Wall;
   `/crm/deals` for pipeline stages.

## Channel prompt cookbook

### Telegram (linked account required)

- `/leads find plumbers in Leeds` - queue discovery (Soft Wall before enroll)
- `/leads approve` / `/leads approve <id>` - Soft Wall CRM approvals
- `/leads digest` - funnel digest with `/crm/*` deep links
- `/crm ask <question>` - workspace-scoped CRM ask-data

Unauthorised or unlinked chats are denied. Signed Soft Wall tokens are short-lived,
single use, scoped, and expire.

### Web / agent tools (toolset `crm`)

- `crm_search`, `crm_get`, `crm_upsert_lead`, `crm_upsert_contact`
- `crm_list_create`, `crm_list_add_members`, `crm_enroll_list` (Soft Wall)
- `crm_set_stage`, `crm_ask`, `crm_suppress`, `crm_offer_booking`
- Sheet: `sheet_preprocess_propose`, `sheet_preprocess_apply` (Soft Wall)

Prefer GUI Soft Wall for production enroll and kill-switch resume.

## Packs

| Pack id | Docs | Adapters (summary) |
| --- | --- | --- |
| `generic` | `docs/features/crm-packs/generic.md` | CH, CSV, web_directory, fake (enabled) |
| `property` | `docs/features/crm-packs/property.md` | CSV/CH/web enabled; portal HTTP flagged/stub |
| `health_social` | `docs/features/crm-packs/health_social.md` | CSV/directory; CQC stub; Soft Wall enroll always |

Manifests: `src/keprix/discovery/packs/*.yaml`

## Packages

- `src/keprix/crm/` - domain model, store, enroll glue, compliance, inbox, outbox
- `src/keprix/sheet_preprocess/` - domain-agnostic sheet flow
- `src/keprix/discovery/` - adapters, jobs, packs
- Soft Wall: `src/keprix/outreach/` (glue only; do not fork)
- Booking: `src/keprix/vical/`

## Tests and sign-off

- pytest: `tests/crm/`, `tests/sheet_preprocess/`, `tests/discovery/`
- Frontend smoke: `tests/frontend/test_discovery_crm_gate.py`
- Sign-off: `docs/architecture/agentic-crm-signoff.md`
