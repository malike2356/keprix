# keprix - Prompt 59: Reference Agent Adoption Release Map

## Context

Read `00a-product-vision-and-agent-consolidation-map.md` for the expanded reference-agent consolidation model.

Prompts 51 through 58 adopt capabilities from LangGraph, CrewAI, LaVague, TaskWeaver, SWE-agent, and AutoGen. This prompt ties them together into a coherent keprix release so the features do not become disconnected modules.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Files To Create

```text
docs/reference-agent-adoption-map.md
docs/keprix-playbook-runtime.md
docs/keprix-agent-teams.md
docs/keprix-browser-engine.md
docs/keprix-analytics-workspace.md
docs/keprix-self-coding.md
docs/keprix-tool-adapters.md
docs/keprix-evals-observability.md
docs/keprix-agent-studio.md
docs/reference-agent-adoption-release-checklist.md
tests/integration/test_reference_adoption_smoke.py
```

## Required Integration Map

Document and wire the dependency order:

1. Prompt 51 durable playbook runtime.
2. Prompt 52 crews and flows on top of runtime.
3. Prompt 58 multi-agent messaging used by crews.
4. Prompt 56 tool adapter registry used by agents.
5. Prompt 53 browser engine exposed as tools and playbook nodes.
6. Prompt 54 analytics workspace exposed as tools and playbook nodes.
7. Prompt 55 self-coding exposed as governed project builder tools.
8. Prompt 57 evals and traces applied to all above.

## Unified Navigation

Add consistent UI entries:

- Playbooks.
- Agent Teams.
- Browser.
- Analytics.
- Coding.
- Tools.
- Evals.
- Agent Studio.

Do not create a different visual language for each entry point.

## Shared Policies

All modules must use the same:

- Approval system.
- Trace system.
- Tool risk registry.
- Workspace artifact store.
- Credential vault.
- Feature gate.
- Scout bridge events where configured.

## Feature Gates

Map capabilities:

Free local owner:

- Durable playbooks.
- Local agent teams.
- Local analytics.
- Local coding.
- Local browser dry run.
- Local evals.

Paid add-on (commercial stack only):

- Managed cloud connectors.
- Hosted sandbox pools.
- Premium search and scraping connectors.
- Advanced browser execution.
- Team collaboration.

Enterprise or Scout:

- Full Scout governance.
- Enterprise trust attestation.
- Shared approval policies.
- Central audit export.

## Acceptance Criteria

- Docs clearly show what came from each reference project and why.
- UI navigation is consistent.
- All adopted modules share approval, tracing, tools, vault, and feature gate primitives.
- Smoke test creates a playbook that calls one crew, one browser dry run, one analytics dry run, and one eval trace.
- No operator-facing text uses deprecated recipe terminology.
- No em dash or en dash characters in new docs.
