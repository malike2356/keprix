# Agentic CRM programme sign-off

**Date:** 2026-08-08
**Programme:** 429-450 + 466 + 506-515 (Must)
**Verdict:** READY
**Nice wave:** 452-465 remain pending (451 satisfied by Must 508)

Writing style: plain ASCII only.

## Scope of this verdict

Core funnel APIs, Soft Wall glue, compliance controls, operator console GUI,
visual pipeline board, workflow canvas, run replay, metrics, analytics, ops
centre, and Must sign-off evidence are READY. Unselected Nice prompts are not
claimed.

## GUI surfacing gate (466 Acceptance)

| Check | Status | Operator path |
| --- | --- | --- |
| Discover -> Soft Wall list -> enroll -> reply inbox without API tools | PASS | `/crm/discover` -> `/crm/jobs` -> `/crm/lists/[id]` Soft Wall enroll -> `/crm/inbox` |
| Kill switch visible and Soft Wall toggleable | PASS | `/crm` strip + `/crm/settings` (resume Soft Wall) |
| Dead-letter send on `/crm/outbox` with Soft Wall retry | PASS | `/crm/outbox` Retry on failed/dead_letter |
| Merge suggestion Soft Wall from `/crm/merges` | PASS | Soft Wall apply / reject |
| Contactability deny blocks enroll UI | PASS | List enroll preflight + `/crm/contactability` |
| Accounts and deals CRUD from GUI | PASS | `/crm/accounts`, `/crm/deals` (+ detail) |
| Nav entries / tabs for IA table | PASS | Sidebar CRM cluster + `CrmTabNav` |
| Frontend smoke / route guards | PASS | `tests/frontend/test_discovery_crm_gate.py` |

## Visual gate (515 Acceptance)

| Check | Status | Evidence |
| --- | --- | --- |
| Contract ids/versions/workspace scope | PASS | `tests/crm/test_visual_crm.py`, `test_visual_e2e_signoff.py` |
| Pipeline board Soft Wall stage moves | PASS | `/crm/pipeline` + preview/commit APIs |
| Workflow canvas validate/simulate/publish | PASS | `/crm/workflows/[id]` |
| Run replay + inspector | PASS | `/crm/runs/[id]` + inspector |
| Metrics + analytics drill-down | PASS | `/crm/analytics` + semantic layer |
| Ops centre | PASS | `/crm/ops` |
| Sign-off doc | PASS | `docs/architecture/visual-crm-signoff.md` |

Honest deferred polish (not blocking READY): full canvas multi-select/undo,
WebSocket live transport (polling ships), Sankey/heatmap chart polish.

## Hardening review checklist (ref-429)

| Requirement | Evidence |
| --- | --- |
| Cross-workspace denial | `tests/crm/test_crm_store.py`, route tools tests, visual isolation |
| No mutation before enrich approval | sheet Soft Wall apply; `tests/crm/test_sheet_preprocess_routes.py` |
| No overwrite of non-empty cells | sheet_preprocess processor tests |
| No send without eligibility / approval / readiness / suppression | enroll preflight + deliverability + compliance tests |
| Retry idempotency (lead/enroll/send/reply/booking) | enroll / outbox / engagement / visual CRM tests |
| Reply / unsub / complaint / bounce / kill / takeover stop sends | engagement + compliance + settings GUI |
| Provenance visible | merges field diff; CRM detail editors |
| LLM outage non-AI path | sheet propose without model; discovery degrade `not_configured` |
| Retention / export / correction / deletion / suppression runbooks | `docs/features/crm-compliance.md` + GUI actions |
| Staged pilot caps + rollback | Pilot plan below |
| GUI paths for Soft Wall Musts | tables above |

## Feature flag / cutover

- Flag id: `crm_funnel` (env tag `KEPRIX_CRM_FUNNEL`), default **on**.
- When off: nav hides `crm`, `crm-enrich`, `crm-discover`, `crm-jobs` for
  non-admin roles (`FLAG_NAV_GATES` in `navigation.py`).
- Kill switch: `/crm/settings` pause immediate; resume Soft Wall gated.
- Contabo / carinaai.uk: **not deployed** for this sign-off; marketing site
  unaffected.

## Pilot (capped, non-production)

| Item | Value |
| --- | --- |
| Owner | Workspace operator (owner designate) |
| Observation window | 7 days after first Soft Wall enroll |
| Caps | Cadence max emails/week/contact (settings default 3); budget strip on deliverability |
| Complaint ceiling | Stop if complaint rate breaches deliverability thresholds |
| Rollback | Workspace kill switch ON; disable `crm_funnel` nav for non-admins; Soft Wall reject pending enrolls |
| Stop procedure | `/crm/settings` Pause outreach -> `/crm/outbox` cancel pending -> `/crm/suppressions` add addresses |

Do not default-on broader production workspaces until pilot exits clean.

## Docs shipped

- `docs/features/agentic-crm.md`
- `docs/features/crm-packs/{generic,property,health_social}.md`
- `docs/architecture/visual-crm-information-architecture.md`
- `docs/architecture/visual-crm-operator-runbook.md`
- `docs/architecture/visual-crm-signoff.md`
- Self-knowledge: `docs/self-knowledge/parity/agentic-crm-*.md`
- Optional helper: `scripts/e2e-crm-funnel.sh`

## Test evidence (2026-08-08)

```bash
cd /opt/lampp/htdocs/verlox/keprix
.venv/bin/pytest tests/crm/test_visual_crm.py tests/crm/test_visual_e2e_signoff.py -q
# 9 passed
```

Earlier core suite (78 passed) covered CRM/discovery/sheet/frontend Soft Wall gate.

## Archive notes

Must prompts 429-450, 466, and 506-515 are archived under
`1st-plan/1st-prompt/prompts-archive/keprix-agentic-crm-lead-gen/`.
Prompt 451 archived as satisfied-by-508.
Nice prompts 452-465 remain in pending.

## Verdict

**READY** for the Must CRM programme (core + visual).
