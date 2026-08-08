# Prompt 466 / 22: CRM operator console and GUI surfacing pack (Must)

**Status: COMPLETED 2026-08-08** (pending parent archive; do not leave orphan)

## What was built

- Operator console IA complete: jobs, inbox, deliverability, outbox, merges,
  contactability, accounts/deals, workflows Soft Wall publish, settings kill switches
- Overview kill-switch strip; honest quick-link copy (no later stubs)
- First-class `/crm/merges` page; `crm_funnel` gates all CRM sidebar nav ids
- Extended frontend smoke for Soft Wall action markers + docs sitemap

**Series:** 429-466  
**Depends on:** 432, 436, 442, 443, 444, 448  
**Blocks:** 450 (Must sign-off must include these surfaces)  
**Writing style:** plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Hardening and funnel Musts must not ship as API/agent-only. Operators need
viewable workspace GUI for jobs, deliverability, takeover, outbox, provenance,
contactability, accounts/deals, nurture, and kill switches.

## Goal

Ship a complete **CRM operator console** under `/crm` (and Soft Wall deep links)
so every Must capability is surfaceable without curl or Telegram-only use.

## Nav and IA (Must)

Sync `navigation.py` + `frontend/src/lib/navigation.ts`. Suggested structure:

| Route | Purpose |
| --- | --- |
| `/crm` | Overview: funnel KPIs, Soft Wall pending, kill-switch status |
| `/crm/accounts`, `/crm/accounts/[id]` | Account CRUD + provenance |
| `/crm/leads`, `/crm/leads/[id]` | Lead CRUD (extend 432) |
| `/crm/contacts`, `/crm/contacts/[id]` | Contact CRUD + consent |
| `/crm/deals`, `/crm/deals/[id]` | Deal CRUD + stage + attribution hooks |
| `/crm/lists`, `/crm/lists/[id]` | Lists + enroll (432/442) |
| `/crm/discover` | Discovery run form (437) |
| `/crm/jobs` | Discovery + enrich job history |
| `/crm/enrich` | Sheet preprocess (434) |
| `/crm/inbox` | Engagement / replies / takeover queue |
| `/crm/workflows` | Nurture list + link to Soft Wall sequences; Nice 451 adds canvas |
| `/crm/deliverability` | Sender readiness, bounces, complaints, budgets |
| `/crm/outbox` | Outbox, dead letters, idempotent send status |
| `/crm/merges` | Identity merge suggestions Soft Wall |
| `/crm/contactability` | Per-person/channel/purpose decisions |
| `/crm/suppressions` | Suppression manager (448) |
| `/crm/settings` | Kill switches, cadence caps, pack flags, budgets |

Reuse Soft Wall approval inbox; deep-link CRM objects with `?approval=` / mesh ids.

## Must-have screens (detail)

### 1. Jobs (`/crm/jobs`)
- Table: adapter, status, started/finished, counts, cost estimate, Soft Wall state.
- Actions: cancel, retry dead-letter, open List draft, Soft Wall materialize.
- Empty and failed states honest.

### 2. Inbox / takeover (`/crm/inbox`)
- Tabs: replies, Soft Wall stage suggestions, human takeover, complaints.
- Claim, assign, pause automation, resume Soft Wall.
- SLA due indicators (Nice 453 can deepen; Must shows queue).

### 3. Deliverability (`/crm/deliverability`)
- Sender domain checklist (SPF/DKIM/DMARC guidance links, verified flag).
- Bounce/complaint rates, warm-up note, workspace/campaign kill switches.
- Budget remaining (enrich + send). Soft Wall to flip kill switch off.

### 4. Outbox (`/crm/outbox`)
- Pending, sent, failed, dead-letter rows with idempotency key.
- Retry Soft Wall-gated; never silent double-send.

### 5. Merges (`/crm/merges`)
- Suggested merges from identity resolution; show field provenance diff.
- Soft Wall approve/reject; never auto-merge consent across people.

### 6. Contactability (`/crm/contactability`)
- Grid: person x channel x purpose x decision (allow/deny/needs_review).
- Bulk Soft Wall; distinct from discovery results.

### 7. Accounts and Deals
- Full list/detail CRUD; activities; related leads/contacts; Soft Wall on paying.

### 8. Workflows (Must-thin)
- List nurture workflows/sequences with status, enroll counts, Soft Wall publish.
- Edit may deep-link Soft Wall until Nice 451 canvas ships; Must must still
  **view, pause, activate, Soft Wall publish** from GUI.

### 9. Soft Wall CRM panel
- On `/crm`: pending CRM-related approvals (enrich, enroll, merge, kill switch).
- Approve/reject without leaving CRM.

## Cross-cutting UI rules

1. Every Soft Wall-gated API action in 429-450 has a matching button or panel.
2. Empty states: no fake demo data.
3. Mobile-usable tables or card fallbacks.
4. Deep links: `/crm/leads/{id}`, Soft Wall item -> CRM object, Telegram digest links.
5. Feature flag `KEPRIX_CRM_FUNNEL` hides nav when off.
6. Frontend smoke tests for all routes above (extend 450).
7. Docs sitemap in `docs/features/agentic-crm.md` matches shipped routes.

## Acceptance

- [ ] Operator can run discover -> Soft Wall list -> enroll -> see reply in inbox without API tools
- [ ] Kill switch visible and toggleable under Soft Wall
- [ ] Dead-letter send visible on `/crm/outbox` with Soft Wall retry
- [ ] Merge suggestion Soft Wall from `/crm/merges`
- [ ] Contactability deny blocks enroll UI with clear reason
- [ ] Accounts and deals CRUD from GUI
- [ ] Nav entries present for all routes in table
- [ ] `pnpm`/frontend smoke or pytest frontend route guards green

## Done When

Must sign-off (450) cannot mark READY if any Must capability lacks a GUI path
(Telegram-only is not enough for Must).

## Explicit non-goals

- Full visual workflow canvas (Nice 451)
- SLA round-robin polish (Nice 453) beyond basic takeover queue
- Attribution report polish (Nice 465) beyond deals page fields
