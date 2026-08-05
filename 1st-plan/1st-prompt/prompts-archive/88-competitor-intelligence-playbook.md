# keprix - Prompt 88: Competitor Intelligence Playbook

## Context

Build the Competitor Intelligence playbook for Opportunity Engine.

This playbook finds competitors already selling to the selected ICP and analyses their positioning, funnels, ads, proof, pricing, and content strategy. The goal is not to copy competitors. The goal is to understand the market standard and find ethical differentiation.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/opportunity/playbooks/competitor_intelligence.py
backend/opportunity/templates/competitor-intelligence-system.md
backend/opportunity/templates/competitor-intelligence-report.md
tests/opportunity/test_competitor_intelligence.py
```

## Inputs

- `03-icp.md`
- `05-offer-doc.md`
- Geography.
- Optional competitor seed list.
- Optional banned domains.

## Sources

Use public sources only:

- Search results.
- Competitor websites.
- Landing pages.
- Public case studies.
- Public ad libraries.
- Public social profiles.
- Review platforms.
- Marketplace listings.

Do not bypass paywalls. Do not scrape private accounts. Do not impersonate customers. Do not submit forms unless the user explicitly approves.

## Output Artifact

Write:

```text
workspace/opportunities/{slug}/04-competitors.md
```

Structure:

```markdown
# Competitor Intelligence

## Competitor Map

| Competitor | Segment | Offer | ICP | Pricing Signal | Funnel Type | Proof | Weakness |
| ---------- | ------- | ----- | --- | -------------- | ----------- | ----- | -------- |

## Funnel Architecture

## Lead Magnets

## Ads And Hooks

## Case Studies And Proof

## Pricing Signals

## Content Strategy

## Differentiation Opportunities

## What Not To Copy

## Citations
```

## Funnel Architecture Fields

For each competitor, capture:

- Traffic source.
- Landing page promise.
- Lead magnet.
- CTA.
- Booking or checkout path.
- Nurture sequence hints.
- Trust proof.
- Objections handled.
- Follow-up mechanism if visible.

## Scoring

Score each competitor:

- `market_strength`: 0 to 100
- `funnel_quality`: 0 to 100
- `proof_strength`: 0 to 100
- `differentiation_gap`: 0 to 100

## Acceptance Criteria

- Finds at least 5 competitors when public data exists.
- Separates direct competitors from adjacent competitors.
- Captures citations for every factual claim.
- Flags unverified pricing.
- Produces a clear differentiation recommendation.
- Tests cover duplicate competitor merging, citation enforcement, and no-private-source policy.

