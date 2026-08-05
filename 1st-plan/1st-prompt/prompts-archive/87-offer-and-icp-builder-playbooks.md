# keprix - Prompt 87: Offer Builder and ICP Builder Playbooks

## Context

Build two connected Opportunity Engine playbooks:

1. Offer Builder
2. ICP Builder

The Offer Builder turns market pain into sellable offers. The ICP Builder defines who the offer is for and where to find them.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/opportunity/playbooks/offer_builder.py
backend/opportunity/playbooks/icp_builder.py
backend/opportunity/templates/offer-builder-system.md
backend/opportunity/templates/icp-builder-system.md
tests/opportunity/test_offer_builder.py
tests/opportunity/test_icp_builder.py
```

## Offer Builder Inputs

- `01-market-demand.md`
- `02-pain-mining.md`
- User constraints.
- Available capabilities in this keprix instance.
- Optional existing business assets.

## Offer Builder Output

Write:

```text
workspace/opportunities/{slug}/05-offer-doc.md
workspace/opportunities/{slug}/06-pricing.md
```

Offer doc structure:

```markdown
# Offer Doc

## Offer Name

## Who It Is For

## Pain It Solves

## Core Promise

## Unique Mechanism

## Deliverables

## What Is Included

## What Is Not Included

## Proof Needed

## Guarantee Options

## Risk And Compliance Notes

## Implementation Requirements

## Sales Angle

## Internal Agent Notes
```

Pricing structure:

```markdown
# Pricing Strategy

## Pricing Hypotheses

| Tier | Price | Buyer Fit | Delivery Cost | Margin Risk | Notes |
| ---- | ----- | --------- | ------------- | ----------- | ----- |

## Competitor Price Anchors

## Labour Cost Comparison

## Recommended Pricing Test

## Risks
```

## ICP Builder Inputs

- Offer doc.
- Pain mining report.
- Demand report.

## ICP Builder Output

Write:

```text
workspace/opportunities/{slug}/03-icp.md
```

Structure:

```markdown
# Ideal Customer Profile

## Primary ICP

## Secondary ICPs

## Buyer Persona

## Company Profile

## Buying Trigger

## Budget Indicators

## Where To Find Them

## Decision Makers

## Influencers

## Objections

## Message That Will Resonate

## Disqualification Criteria
```

## Guardrails

- Do not invent proof, case studies, or customer outcomes.
- Do not make guaranteed income claims.
- Do not recommend predatory targeting.
- Add compliance warnings for regulated industries.
- Ask for approval before generating outbound campaigns.

## JSON Update

Update `opportunity.json` with:

```json
{
  "phase": "offer_builder",
  "offer": {},
  "pricing": {},
  "icp": {}
}
```

## Acceptance Criteria

- Creates an offer that maps directly to market pains.
- Creates at least 3 pricing hypotheses.
- Creates a clear primary ICP and at least 2 secondary ICPs.
- Includes disqualification criteria.
- Tests cover false-proof prevention, regulated-industry warnings, and pricing structure.

