# keprix - Prompt 90: Offer Doc and Agent Memory Playbook

**Status:** Completed. Implementation in `src/keprix/opportunity/playbooks/offer_doc_generator.py`,
`src/keprix/opportunity/templates/canonical-offer-doc.md`,
`src/keprix/opportunity/templates/agent-memory-brief.md`, and
`tests/opportunity/test_offer_doc_generator.py` (57 opportunity tests pass).

## Context

Build the canonical Offer Doc and Agent Memory playbook for Opportunity Engine.

The offer doc is the single source of truth for future agents. Every later playbook must read it before generating assets, campaigns, funnels, or launch actions.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/opportunity/playbooks/offer_doc_generator.py
backend/opportunity/templates/canonical-offer-doc.md
backend/opportunity/templates/agent-memory-brief.md
tests/opportunity/test_offer_doc_generator.py
```

## Inputs

- Market demand.
- Pain mining.
- ICP.
- Competitor intelligence.
- Pricing.
- Validation score.

## Required Artifacts

Update or create:

```text
workspace/opportunities/{slug}/05-offer-doc.md
workspace/opportunities/{slug}/agent-memory-brief.md
```

## Offer Doc Required Sections

```markdown
# Canonical Offer Doc

## Offer Name

## One-Line Positioning

## Target Market

## Primary ICP

## Core Pain

## Core Promise

## Unique Mechanism

## Productised Deliverables

## Pricing

## Guarantee

## Proof Needed

## Competitor Positioning

## Differentiation

## Funnel Strategy

## Content Strategy

## Outreach Strategy

## Risk And Compliance Notes

## Words To Use

## Words To Avoid

## Claims Agents May Make

## Claims Agents Must Not Make

## Approval Rules

## Open Questions
```

## Agent Memory Brief

Write a concise version for later agent context:

```markdown
# Agent Memory Brief

You are working on the opportunity named: ...

Use this positioning:

Use this ICP:

Use these pains:

Use this unique mechanism:

Never make these claims:

Require approval before:
```

## Memory Integration

If keprix has workspace memory enabled:

- Store the agent memory brief as opportunity-scoped memory.
- Tag it with `opportunity_id`, `offer`, `icp`, and `launch`.
- Do not inject it into unrelated workspaces.

## Acceptance Criteria

- Later playbooks can load the canonical offer doc by opportunity ID.
- The doc contains allowed and forbidden claims.
- The memory brief is concise enough for prompt injection.
- Tests cover scoped memory, forbidden claims, and missing validation score handling.

