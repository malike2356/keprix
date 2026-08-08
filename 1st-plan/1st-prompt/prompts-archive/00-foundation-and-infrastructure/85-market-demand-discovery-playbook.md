# keprix - Prompt 85: Market Demand Discovery Playbook

## Context

Build the first Opportunity Engine playbook: Market Demand Discovery.

The purpose is to let keprix find demand signals in any niche before the user decides what to sell. This playbook should not assume the user already knows the best opportunity. It should discover and rank possible demand pockets.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/opportunity/playbooks/
  __init__.py
  market_demand.py
backend/opportunity/templates/
  market-demand-system.md
  market-demand-report.md
tests/opportunity/test_market_demand.py
```

## Inputs

The playbook accepts:

- Broad niche, for example "AI automation for estate agents".
- Geography, optional.
- Buyer type, optional.
- Budget range, optional.
- Exclusions, optional.
- Research depth: quick, standard, deep.

## Research Sources

Use available tools and integrations in this order:

1. Existing workspace knowledge.
2. SearXNG or configured web search.
3. Public forums and communities.
4. Search trends where available.
5. Review sites and marketplaces.
6. Job boards.
7. Ads libraries where available.
8. Competitor landing pages.
9. Public social content.

Do not scrape behind logins. Do not bypass rate limits. Do not collect personal data beyond public business context.

## Output Artifact

Write:

```text
workspace/opportunities/{slug}/01-market-demand.md
```

Use this structure:

```markdown
# Market Demand Discovery

## Search Brief

## Demand Pockets

| Rank | Demand Pocket | Buyer | Pain | Urgency | Evidence Strength | Monetisation Potential |
| ---- | ------------- | ----- | ---- | ------- | ----------------- | ---------------------- |

## Signals Found

## Repeated Questions

## Buying Triggers

## Existing Spend Signals

## Gaps In Existing Solutions

## Market Risks

## Recommended Opportunity To Explore Next

## Citations
```

## Scoring

Each demand pocket must receive:

- `urgency_score`: 0 to 100
- `evidence_score`: 0 to 100
- `willingness_to_pay_score`: 0 to 100
- `competition_gap_score`: 0 to 100
- `overall_demand_score`: weighted score

Weights:

- Urgency: 30
- Evidence: 25
- Willingness to pay: 25
- Competition gap: 20

## JSON Update

Update `opportunity.json` with:

```json
{
  "phase": "market_demand",
  "status": "researching",
  "demand_pockets": [],
  "recommended_demand_pocket": "",
  "citations": []
}
```

## Acceptance Criteria

- Produces at least 5 demand pockets for standard and deep research.
- Each demand pocket includes evidence and citations.
- The report distinguishes strong evidence from weak inference.
- The recommended demand pocket is justified.
- No fabricated market sizes or uncited claims.
- Tests cover scoring weights, missing citations, and empty-search fallback.

