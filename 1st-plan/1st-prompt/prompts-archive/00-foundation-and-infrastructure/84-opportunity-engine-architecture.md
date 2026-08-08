# keprix - Prompt 84: Opportunity Engine Architecture

**Status:** Completed. Implementation in `src/keprix/opportunity/`,
`src/keprix/opportunity/routes.py`, `keprix_cli/opportunity_commands.py`, and
`tests/opportunity/test_opportunity_engine.py`.

## Context

You are adding an optional feature to keprix called the Opportunity Engine.

The goal is to move keprix beyond task execution. The user should be able to ask keprix to discover a market opportunity, validate it, design an offer, generate launch assets, and prepare an execution plan. keprix may research, reason, write, design, and prepare integrations autonomously. It must not publish, spend money, contact leads, modify CRM records, or launch ads without explicit human approval.

Use the product term "playbook". Do not use deprecated recipe terminology in operator-facing copy, docs, API responses, UI, CLI help, or generated workspace files.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## What You Are Building

Create the foundation for a new workspace mode:

```text
Opportunity Mode
```

This mode creates and manages opportunity workspaces under:

```text
workspace/opportunities/{slug}/
```

Each opportunity workspace must contain structured files that future agents can read and update:

```text
01-market-demand.md
02-pain-mining.md
03-icp.md
04-competitors.md
05-offer-doc.md
06-pricing.md
07-funnel.md
08-content-assets.md
09-ads.md
10-sales-deck.md
11-launch-plan.md
12-validation-score.md
13-approval-log.md
14-growth-loop.md
opportunity.json
```

## Required Backend Modules

Create:

```text
backend/opportunity/
  __init__.py
  models.py
  workspace.py
  orchestrator.py
  approvals.py
  scoring.py
  citations.py
  safety.py
  registry.py
```

### models.py

Define Pydantic models:

```python
OpportunityStatus = Literal[
  "draft",
  "researching",
  "validating",
  "assets_ready",
  "approval_required",
  "launch_ready",
  "launched",
  "paused",
  "archived",
]

OpportunityPhase = Literal[
  "market_demand",
  "pain_mining",
  "offer_builder",
  "icp_builder",
  "competitor_intelligence",
  "validation_score",
  "offer_doc",
  "asset_factory",
  "launch_orchestrator",
  "growth_loop",
]
```

Models:

- `OpportunityWorkspace`
- `OpportunityRequest`
- `OpportunityArtifact`
- `OpportunityCitation`
- `OpportunityScore`
- `OpportunityApproval`
- `OpportunityExecutionPlan`
- `OpportunityIntegrationRef`

Every model must include `workspace_id`, `opportunity_id`, `created_at`, `updated_at`, and `source`.

### workspace.py

Implement:

- `create_opportunity_workspace(request)`
- `load_opportunity_workspace(opportunity_id)`
- `write_artifact(opportunity_id, filename, content, metadata)`
- `read_artifact(opportunity_id, filename)`
- `append_approval_log(opportunity_id, event)`
- `update_opportunity_json(opportunity_id, patch)`

Use safe path handling. No user input may escape `workspace/opportunities/`.

### orchestrator.py

Implement a phase runner that can execute one phase or the full sequence:

```python
run_opportunity_phase(opportunity_id, phase, options)
run_opportunity_pipeline(opportunity_id, options)
```

The pipeline order is:

1. Market demand discovery
2. Pain mining
3. Offer builder
4. ICP builder
5. Competitor intelligence
6. Validation scoring
7. Offer doc generation
8. Asset factory
9. Launch orchestrator
10. Growth loop setup

Each phase must:

- Read existing artifacts.
- Write its own artifact.
- Add citations where research was used.
- Update `opportunity.json`.
- Emit an event to the existing observability layer if available.

### approvals.py

Implement approval gates for risky actions:

- Sending outreach.
- Publishing posts.
- Creating or editing ads.
- Spending money.
- Updating CRM records.
- Sending email sequences.
- Publishing landing pages.
- Charging customers.
- Exporting personal data.

Default policy: block and require explicit approval.

### safety.py

Implement safety checks:

- No fabricated citations.
- No scraping behind login pages.
- No personal data collection unless a connected integration and lawful basis are configured.
- No ad launch without approval.
- No competitor impersonation.
- No claims that cannot be supported by artifacts.
- No medical, legal, or financial promises without compliance warning.

## API Surface

Create routes under:

```text
backend/api/opportunity.py
```

Routes:

```text
POST /api/opportunities
GET /api/opportunities
GET /api/opportunities/{id}
POST /api/opportunities/{id}/run
POST /api/opportunities/{id}/phase/{phase}
GET /api/opportunities/{id}/artifacts/{filename}
POST /api/opportunities/{id}/approve
POST /api/opportunities/{id}/pause
POST /api/opportunities/{id}/archive
```

Use existing auth, workspace, and feature gate patterns.

## CLI Surface

Add:

```text
keprix opportunity new
keprix opportunity run
keprix opportunity phase
keprix opportunity status
keprix opportunity approve
```

## Acceptance Criteria

- A user can create an opportunity workspace from a niche, market, or broad business goal.
- The workspace files are created with stable names.
- The pipeline can run phase by phase.
- Risky execution actions produce approval requests, not live actions.
- All generated claims with research support include citations.
- No operator-facing text uses deprecated recipe terminology.
- Tests cover safe path handling, approval gates, phase order, and artifact creation.
