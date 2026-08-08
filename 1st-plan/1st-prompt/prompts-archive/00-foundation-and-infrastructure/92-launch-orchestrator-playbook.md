# keprix - Prompt 92: Launch Orchestrator Playbook

**Status:** Completed. Implementation in `src/keprix/opportunity/playbooks/launch_orchestrator.py`,
`src/keprix/opportunity/integrations.py`, `templates/launch-plan-template.md`, and
`tests/opportunity/test_launch_orchestrator.py` (66 opportunity tests pass).

## Context

Build the Launch Orchestrator playbook for Opportunity Engine.

This playbook prepares execution across CRM, email, social, ads, analytics, forms, website, and Stripe. It must be approval-led. It may prepare actions automatically, but it must not execute risky actions without explicit approval.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
backend/opportunity/playbooks/launch_orchestrator.py
backend/opportunity/integrations.py
backend/opportunity/templates/launch-plan-template.md
tests/opportunity/test_launch_orchestrator.py
```

## Integrations

Support optional connectors where available:

- CRM.
- Email platform.
- Ads manager.
- Social account.
- Website or landing page builder.
- Analytics.
- Stripe.
- Calendar.
- Form tool.

If a connector is missing, generate setup instructions and a pending connector task. Do not fail the whole launch plan.

## Output Artifact

Write:

```text
workspace/opportunities/{slug}/11-launch-plan.md
```

Structure:

```markdown
# Launch Plan

## Launch Goal

## Required Approvals

## Connected Integrations

## Missing Integrations

## Pre-Launch Checklist

## CRM Setup

## Email Sequence Setup

## Social Publishing Plan

## Ads Plan

## Landing Page Plan

## Analytics Plan

## Stripe Or Checkout Plan

## Rollback Plan

## Launch Approval
```

## Approval Gates

Require approval for:

- Sending any email or message.
- Uploading a lead list.
- Publishing a landing page.
- Publishing social posts.
- Creating ads.
- Editing active ads.
- Setting budgets.
- Charging customers.
- Creating Stripe products or prices.
- Updating CRM lifecycle stage.

Approval records must include:

- Action.
- Risk level.
- Preview.
- Integration.
- Requested by.
- Approved by.
- Timestamp.
- Result.

## Dry Run Mode

Implement dry run as the default:

```python
run_launch_plan(opportunity_id, dry_run=True)
```

Dry run returns the exact actions that would be taken.

## Acceptance Criteria

- Default execution is dry run.
- Risky actions are blocked without approval.
- Missing integrations become setup tasks.
- Approval log is written to `13-approval-log.md`.
- Tests cover dry run, approval-required actions, missing connector fallback, and rollback plan generation.

