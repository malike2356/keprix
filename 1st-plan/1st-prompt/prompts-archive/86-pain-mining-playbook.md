# keprix - Prompt 86: Pain Mining Playbook

## Context

Build the Pain Mining playbook for Opportunity Engine.

This playbook reads `01-market-demand.md` and discovers what the target market is struggling with in the language they actually use. The goal is to extract market pain, urgency, failed alternatives, objections, and emotional triggers.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/opportunity/playbooks/pain_mining.py
backend/opportunity/templates/pain-mining-system.md
backend/opportunity/templates/pain-mining-report.md
tests/opportunity/test_pain_mining.py
```

## Inputs

- Opportunity workspace.
- Demand pocket selected from phase 1.
- Optional ICP hints.
- Optional banned sources.

## Required Analysis

Extract:

- Top pains.
- Repeated phrases from the market.
- Failed alternatives.
- Current workarounds.
- Emotional triggers.
- Business cost of the pain.
- Buying urgency.
- Objections to buying.
- Trust barriers.
- Compliance or ethical risks.

## Output Artifact

Write:

```text
workspace/opportunities/{slug}/02-pain-mining.md
```

Use this structure:

```markdown
# Pain Mining

## Selected Demand Pocket

## Top Market Pains

| Rank | Pain | Exact Language | Evidence | Urgency | Business Cost |
| ---- | ---- | -------------- | -------- | ------- | ------------- |

## Failed Alternatives

## Existing Workarounds

## Emotional Triggers

## Purchase Objections

## Trust Barriers

## Compliance And Ethical Risks

## Messaging Angles

## Citations
```

## Exact Language Rules

When quoting user or market language:

- Keep quotes short.
- Attribute source.
- Do not include private personal data.
- Do not quote more than needed.
- Paraphrase where direct quotation is not necessary.

## JSON Update

Update `opportunity.json` with:

```json
{
  "phase": "pain_mining",
  "top_pains": [],
  "objections": [],
  "messaging_angles": [],
  "citations": []
}
```

## Acceptance Criteria

- Produces at least 7 market pains for standard and deep research.
- Separates evidence from inference.
- Flags compliance and ethical risks.
- Does not use private personal data.
- Tests cover quote sanitisation, citation requirements, and pain ranking.
