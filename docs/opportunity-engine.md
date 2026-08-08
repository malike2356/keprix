# Opportunity Engine

The Opportunity Engine helps operators research, validate, and prepare go-to-market work for a new niche without automatically spending money or publishing live assets. It runs a fixed sequence of **playbooks** (phases) that write markdown artifacts into a portable workspace folder.

## What it does

1. **Market demand** (`market_demand`): scores demand signals and writes `01-market-demand.md`.
2. **Pain mining** (`pain_mining`): extracts buyer pains with sanitised quotes in `02-pain-mining.md`.
3. **Offer builder** (`offer_builder`): drafts offer positioning in `05-offer-doc.md` and `06-pricing.md`.
4. **ICP builder** (`icp_builder`): defines ideal customer profile in `03-icp.md`.
5. **Competitor intelligence** (`competitor_intelligence`): competitor notes with citation rules in `04-competitors.md`.
6. **Validation score** (`validation_score`): composite score in `12-validation-score.md`; blocks asset generation below 65 unless overridden.
7. **Offer doc** (`offer_doc`): canonical offer document and `agent-memory-brief.md`.
8. **Asset factory** (`asset_factory`): funnel, content, ads, and sales deck drafts plus an `assets/` subfolder.
9. **Launch orchestrator** (`launch_orchestrator`): execution plan in `11-launch-plan.md`; **dry run by default**.
10. **Growth loop** (`growth_loop`): metrics snapshot and ranked experiments in `14-growth-loop.md`.

Approval events are appended to `13-approval-log.md`. Metadata lives in `opportunity.json`.

## What it will not do without approval

The engine never performs risky actions silently. Publishing ads, spending budget, sending outreach, updating CRM records, charging customers, exporting personal data, and similar actions require explicit operator approval. See [opportunity-engine-approval-policy.md](opportunity-engine-approval-policy.md).

## Terminology: playbook

Keprix uses **playbook** for repeatable, phase-based workflows (market demand playbook, launch orchestrator playbook, and so on). Use **playbook** in operator docs, CLI help, and generated workspace files.

## Surfaces (same backend)

| Surface | Entry |
| --- | --- |
| Web UI | Workspace route `/opportunities` |
| REST API | `/api/opportunities/*` (authenticated) |
| CLI | `keprix opportunity new|run|phase|status|artifact|approve` |
| Slash | `/opportunity` in chat (see examples below) |

All surfaces call `src/keprix/opportunity/` orchestration code.

## Web UI

1. Open **Opportunities** in the workspace shell.
2. Create an opportunity with title, niche, market, goal, and geography.
3. Run the full pipeline or individual playbooks from the phase controls.
4. Review artifacts in the artifact viewer; approve gated actions when prompted.
5. Integration status reflects connected CRM, email, ads, and related services.

## CLI

```bash
# Create workspace
keprix opportunity new --title "AI automation for UK estate agents" \
  --niche "UK estate agency operations" --market "UK property services"

# Run all playbooks in order
keprix opportunity run opp-xxxxxxxx

# Run one playbook
keprix opportunity phase opp-xxxxxxxx market_demand

# Status and artifacts
keprix opportunity status opp-xxxxxxxx
keprix opportunity artifact opp-xxxxxxxx 11-launch-plan.md

# Resolve an approval gate
keprix opportunity approve opp-xxxxxxxx create_ad --approve
```

## Slash command

In agent chat, prefix with `/opportunity`:

```text
/opportunity find demand for UK estate agents
/opportunity run pipeline opp-a1b2c3d4
/opportunity run phase market_demand opp-a1b2c3d4
/opportunity prepare launch opp-a1b2c3d4 dry-run
/opportunity status opp-a1b2c3d4
```

Slash parsing lives in `src/keprix/opportunity/slash.py` and is registered with the global slash router.

## Workspace storage

Each opportunity gets an ID like `opp-a1b2c3d4` and a directory under the Keprix workspace root:

```text
{WORKSPACE_ROOT}/opportunities/{opportunity_id}/
  opportunity.json
  01-market-demand.md
  ...
  14-growth-loop.md
  assets/
    landing-page.md
    ad-copy.md
    ...
```

`WORKSPACE_ROOT` defaults from Keprix workspace settings. Artifacts are plain markdown and JSON; copy the folder to archive or move between environments.

## Optional Scout connectors

Scout governance and external data connectors can enrich research playbooks when configured, but **no Scout connector is required** to create an opportunity or run dry-run launch planning. Missing integrations produce manual import templates and setup instructions instead of failing the pipeline.

## Related docs

- [Approval policy](opportunity-engine-approval-policy.md)
- [Integrations](opportunity-engine-integrations.md)
- [Examples](opportunity-engine-examples.md)
- [Changelog automation](operations/changelog-automation.md)
