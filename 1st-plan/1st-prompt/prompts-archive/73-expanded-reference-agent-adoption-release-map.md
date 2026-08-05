# keprix - Prompt 73: Expanded Reference Agent Adoption Release Map

> **Status (2026-07-05):** Shipped Phase 14 release docs (`docs/expanded-reference-agent-release-map.md`, `docs/agent-dna-capability-map.md`, `docs/phase-14-build-order.md`) and integration smoke test (`tests/integration/test_expanded_agent_dna_smoke.py`, 6 tests).

## Context

Prompts 60 through 72 extend keprix with the 12 newly added reference agents. This prompt ties the expanded adoption pack into a coherent release.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create Or Extend

```text
docs/expanded-reference-agent-release-map.md
docs/agent-dna-capability-map.md
docs/phase-14-build-order.md
tests/integration/test_expanded_agent_dna_smoke.py
```

## Dependency Order

Build in this order:

1. Prompt 60 gap audit and matrix.
2. Prompt 66 typed agents, dependency injection, and validation.
3. Prompt 65 handoffs, guardrails, tracing, realtime.
4. Prompt 67 agent app lifecycle and runners.
5. Prompt 68 plugin, memory, planner, interoperability.
6. Prompt 69 document agents and indexing.
7. Prompt 72 production RAG pipelines.
8. Prompt 62 git-native coding UX.
9. Prompt 64 code-agent sandbox and hub tools.
10. Prompt 63 browser harness.
11. Prompt 61 control center.
12. Prompt 70 TypeScript SDK and workflow developer UX.
13. Prompt 71 interfaces and auto-improvement.
14. Prompt 73 release map and smoke tests.

## Unified Product Surface

The expanded release must feel like one keprix product:

- One app shell.
- One approval system.
- One trace viewer.
- One vault.
- One plugin registry.
- One playbook runtime.
- One SDK contract.
- One artifact store.
- One eval format.
- One support export.

## Required Smoke Test

Create a smoke test that:

1. Creates a typed agent.
2. Mounts one plugin.
3. Builds one RAG pipeline.
4. Runs one document query.
5. Runs one browser dry run.
6. Runs one coding dry run.
7. Hands off to one specialist agent.
8. Creates one trace.
9. Generates one improvement proposal.
10. Exports the run as an artifact bundle.

## Boundary Checks

Verify:

- No cybersecurity tooling is added to keprix. That belongs to Petraclus.
- No Carina branding appears in keprix operator-facing surfaces.
- Scout is optional and paid.
- Upstream agent names are only mentioned in internal reference docs.
- New features use "playbook", not deprecated recipe terminology.

## Acceptance Criteria

- Phase 14 docs link prompts 60 through 73.
- Existing prompts 51 through 59 are not duplicated.
- Expanded adoption matrix marks every reference agent as covered.
- Smoke test passes against local fixtures.
- New docs contain no em dash or en dash characters.
