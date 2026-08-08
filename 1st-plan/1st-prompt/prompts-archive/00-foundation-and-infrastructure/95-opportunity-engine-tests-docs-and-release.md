# keprix - Prompt 95: Opportunity Engine Tests, Docs, and Release Readiness

## Context

Complete Opportunity Engine with tests, documentation, examples, and release checks.

This prompt should be built after Prompts 52 through 62.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Test Coverage

Add tests for:

- Opportunity workspace creation.
- Safe path handling.
- Phase runner order.
- Market demand scoring.
- Pain mining quote sanitisation.
- Offer builder false-claim prevention.
- ICP builder output shape.
- Competitor citation enforcement.
- Validation score thresholds.
- Asset factory forbidden claims.
- Launch orchestrator dry run.
- Approval logging.
- Growth loop missing integration fallback.
- API auth.
- CLI commands.
- Slash command parsing.
- UI smoke render.

## Evaluation Fixtures

Create fixtures:

```text
tests/fixtures/opportunity/
  estate-agents-request.json
  borehole-drilling-ghana-request.json
  cybersecurity-consultancy-request.json
  weak-demand-example.json
  regulated-healthcare-example.json
```

Use these to test:

- Normal B2B opportunity.
- Localised African market opportunity.
- Security services opportunity.
- Weak opportunity that should be blocked.
- Regulated industry that needs warnings.

## Documentation

Create:

```text
docs/opportunity-engine.md
docs/opportunity-engine-approval-policy.md
docs/opportunity-engine-integrations.md
docs/opportunity-engine-examples.md
```

Docs must explain:

- What Opportunity Engine does.
- What it will not do without approval.
- How to run from web UI.
- How to run from CLI.
- How to use `/opportunity`.
- How artifacts are stored.
- How to connect CRM, ads, email, social, analytics, and Stripe.
- Why "playbook" is the product term.
- How optional Scout connectors fit without making them required.

## Example Walkthrough

Add an example:

```text
Find and validate a profitable AI automation opportunity for UK estate agents. Build the offer, ICP, funnel, launch assets, and execution plan. Do not publish or spend money without approval.
```

The example must show expected artifact names and approval gates.

## Release Checklist

Add a checklist file:

```text
docs/opportunity-engine-release-checklist.md
```

Checklist:

- All prompts 52 through 62 built.
- Tests pass.
- Docs use "playbook", not deprecated recipe terminology.
- Risky actions require approval.
- No private data collection by default.
- No unsupported claims in generated assets.
- UI, CLI, and slash command all point to same backend.
- Launch actions default to dry run.
- Workspace artifacts are portable.

## Acceptance Criteria

- Opportunity Engine is documented end to end.
- Test suite covers all safety gates.
- Example opportunities can run in dry-run mode.
- Release checklist exists.
- Operator-facing docs, frontend, backend responses, CLI help, and generated workspace files use "playbook" consistently.
- No em dash or en dash characters in new docs or prompts.
