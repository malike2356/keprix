# keprix - Prompt 93: Growth Loop Playbook

**Status:** Completed. Implementation in `src/keprix/opportunity/playbooks/growth_loop.py`,
`src/keprix/opportunity/templates/growth-loop-report.md`, and
`tests/opportunity/test_growth_loop.py` (71 opportunity tests pass).

## Context

Build the Growth Loop playbook for Opportunity Engine.

After launch, keprix should monitor performance, learn from data, and recommend improvements. It should not make live changes without approval.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/opportunity/playbooks/growth_loop.py
backend/opportunity/templates/growth-loop-report.md
tests/opportunity/test_growth_loop.py
```

## Inputs

- Launch plan.
- Connected analytics.
- CRM activity.
- Email performance.
- Ads performance.
- Social performance.
- Form submissions.
- Stripe or checkout events.

All integrations are optional. If not connected, the playbook should provide a manual data import template.

## Output Artifact

Write:

```text
workspace/opportunities/{slug}/14-growth-loop.md
```

Structure:

```markdown
# Growth Loop

## Current Status

## Metrics Snapshot

| Metric | Value | Source | Trend | Notes |
| ------ | ----- | ------ | ----- | ----- |

## Funnel Bottlenecks

## Winning Messages

## Weak Assets

## Recommended Experiments

## A/B Test Queue

## Budget Recommendations

## CRM Follow-Up Recommendations

## Approval Requests

## Next Review Date
```

## Metrics

Support:

- Visits.
- Conversion rate.
- Lead count.
- Cost per lead.
- Reply rate.
- Booked calls.
- Show-up rate.
- Close rate.
- Revenue.
- Refunds.
- Churn.
- Sales cycle length.

## Experiment Suggestions

Each experiment must include:

- Hypothesis.
- Asset to change.
- Expected impact.
- Risk.
- Effort.
- Metric to watch.
- Approval requirement.

## Guardrails

- Do not increase ad budget without approval.
- Do not rewrite live pages without approval.
- Do not contact leads without approval.
- Do not infer sensitive attributes.
- Do not optimise for deceptive or harmful targeting.

## Acceptance Criteria

- Works with no integrations by producing manual import templates.
- Produces ranked experiments.
- Creates approval requests for live changes.
- Updates `opportunity.json` with growth status.
- Tests cover missing integrations, experiment ranking, and approval gating.

