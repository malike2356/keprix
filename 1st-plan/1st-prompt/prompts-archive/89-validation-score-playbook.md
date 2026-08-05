# keprix - Prompt 89: Validation Score Playbook

## Context

Build the Validation Score playbook for Opportunity Engine.

The playbook gives the opportunity a clear score before the user spends time or money building assets. It should be strict. Its job is to prevent weak offers from moving to launch.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/opportunity/playbooks/validation_score.py
backend/opportunity/templates/validation-score-system.md
backend/opportunity/templates/validation-score-report.md
tests/opportunity/test_validation_score.py
```

## Inputs

- `01-market-demand.md`
- `02-pain-mining.md`
- `03-icp.md`
- `04-competitors.md`
- `05-offer-doc.md`
- `06-pricing.md`

## Score Categories

Use a 0 to 100 score for each:

- Demand strength.
- Pain urgency.
- ICP clarity.
- Willingness to pay.
- Competition gap.
- Offer clarity.
- Proof readiness.
- Delivery feasibility.
- Speed to launch.
- Compliance and risk.

## Weighting

```text
Demand strength: 15
Pain urgency: 15
ICP clarity: 10
Willingness to pay: 12
Competition gap: 10
Offer clarity: 12
Proof readiness: 8
Delivery feasibility: 8
Speed to launch: 5
Compliance and risk: 5
```

Compliance and risk is inverted: lower risk creates a higher score.

## Output Artifact

Write:

```text
workspace/opportunities/{slug}/12-validation-score.md
```

Structure:

```markdown
# Validation Score

## Overall Score

## Recommendation

One of:

- Proceed
- Revise offer
- Gather more evidence
- Do not launch

## Score Breakdown

| Category | Score | Weight | Evidence | Improvement |
| -------- | ----- | ------ | -------- | ----------- |

## Biggest Strengths

## Biggest Risks

## What To Improve Before Launch

## Evidence Gaps

## Approval Needed Before Execution
```

## Decision Thresholds

- 80 to 100: Proceed to asset generation.
- 65 to 79: Revise offer before launch.
- 45 to 64: Gather more evidence.
- 0 to 44: Do not launch.

## JSON Update

Update `opportunity.json` with:

```json
{
  "phase": "validation_score",
  "validation": {
    "overall_score": 0,
    "recommendation": "",
    "blocking_risks": [],
    "evidence_gaps": []
  }
}
```

## Acceptance Criteria

- Blocks asset generation by default when score is below 65 unless the user explicitly overrides.
- Gives specific improvement steps.
- Does not hide compliance risk.
- Tests cover weighted scoring, threshold decisions, override logging, and malformed inputs.

