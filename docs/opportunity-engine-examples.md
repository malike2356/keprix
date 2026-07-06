# Opportunity Engine examples

Evaluation fixtures live in `tests/fixtures/opportunity/`. Use them for dry-run testing and as templates for real opportunities.

## UK estate agents (full walkthrough)

**Goal:** Find and validate a profitable AI automation opportunity for UK estate agents. Build the offer, ICP, funnel, launch assets, and execution plan. Do not publish or spend money without approval.

### Request

```json
{
  "title": "AI automation for UK estate agents",
  "niche": "UK estate agency operations",
  "market": "UK property services",
  "goal": "Find and validate a profitable AI automation opportunity for UK estate agents",
  "geography": "United Kingdom",
  "buyer_type": "Estate agency principals and ops managers",
  "research_depth": "standard"
}
```

Fixture file: `tests/fixtures/opportunity/estate-agents-request.json`.

### CLI session

```bash
keprix opportunity new \
  --title "AI automation for UK estate agents" \
  --niche "UK estate agency operations" \
  --market "UK property services" \
  --goal "Find and validate a profitable AI automation opportunity for UK estate agents" \
  --geography "United Kingdom"

# Note the returned opp-xxxxxxxx id, then:
keprix opportunity run opp-xxxxxxxx
keprix opportunity artifact opp-xxxxxxxx 11-launch-plan.md
```

### Expected artifacts (in order)

| File | Playbook |
| --- | --- |
| `01-market-demand.md` | market_demand |
| `02-pain-mining.md` | pain_mining |
| `03-icp.md` | icp_builder |
| `04-competitors.md` | competitor_intelligence |
| `05-offer-doc.md` | offer_builder / offer_doc |
| `06-pricing.md` | offer_builder |
| `12-validation-score.md` | validation_score |
| `07-funnel.md` | asset_factory |
| `08-content-assets.md` | asset_factory |
| `09-ads.md` | asset_factory |
| `10-sales-deck.md` | asset_factory |
| `11-launch-plan.md` | launch_orchestrator |
| `14-growth-loop.md` | growth_loop |
| `13-approval-log.md` | approvals (throughout) |
| `assets/*` | asset_factory drafts |

### Approval gates in the launch plan

A dry-run launch plan lists pending approvals such as:

- `create_ad` before any ad platform call
- `publish_landing_page` before site deploy
- `send_email_sequence` before nurture send
- `update_crm` before pipeline writes
- `spend_money` / `set_ad_budget` before budget changes

Resolve with `keprix opportunity approve` or the web UI before disabling dry run.

### Slash equivalent

```text
/opportunity find demand for UK estate agents
/opportunity run pipeline opp-xxxxxxxx
```

## Borehole drilling, Ghana (localised market)

Fixture: `borehole-drilling-ghana-request.json`.

Tests market demand with geography-specific context. Run:

```bash
keprix opportunity phase opp-xxxxxxxx market_demand
```

Expect `01-market-demand.md` to reference Ghana or borehole services.

## Cybersecurity consultancy (B2B services)

Fixture: `cybersecurity-consultancy-request.json`.

Useful for pain mining and approval-log checks. Run market demand and pain mining playbooks; review `02-pain-mining.md` for sanitised pain quotes.

## Weak demand (blocked assets)

Fixture: `weak-demand-example.json`.

After validation_score, the composite score should fall below 65. The asset_factory playbook returns `blocked: true` unless the operator sets `validation_override` in metadata.

## Regulated healthcare (warnings)

Fixture: `regulated-healthcare-example.json`.

Offer builder and launch playbooks flag regulated industry warnings. Extra human review is required before any approval that could affect patients or clinical claims.

## Dry-run launch only

Keep `launch_dry_run: true` (default) in `opportunity.json` until:

1. Validation score is acceptable.
2. Artifacts are reviewed for unsupported claims.
3. Required approvals are granted.
4. Integrations are connected as needed.

Never approve `spend_money` or `create_ad` for evaluation fixtures in production accounts.
