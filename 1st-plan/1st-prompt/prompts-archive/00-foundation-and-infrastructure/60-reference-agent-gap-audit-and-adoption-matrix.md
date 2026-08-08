# keprix - Prompt 60: Reference Agent Gap Audit and Adoption Matrix

## Context

keprix now has reference clones for every major agent system in `planning/agents-to-adopt/`.

Before adding new features, audit the current keprix prompts and code so builders do not duplicate work that already exists. This prompt creates the adoption matrix that all later prompts in this phase must follow.

## Working Directory

`/opt/lampp/htdocs/verlox/keprix/keprix/`

## Reference To Study

Read:

```text
planning/agents-to-adopt/README.md
planning/agents-to-adopt/REUSE-NOTICE.md
planning/prompts/00a-product-vision-and-agent-consolidation-map.md
planning/prompts/51-langgraph-style-durable-playbook-runtime.md
planning/prompts/52-crewai-style-crews-flows-agent-teams.md
planning/prompts/53-lavague-style-browser-action-engine.md
planning/prompts/54-taskweaver-style-data-analytics-code-workspace.md
planning/prompts/55-swe-agent-style-self-coding-and-patch-trajectories.md
planning/prompts/56-crewai-tool-library-adapter-pack.md
planning/prompts/57-agent-evals-benchmarks-and-trace-observability.md
planning/prompts/58-autogen-style-multi-agent-messaging-and-studio.md
planning/prompts/59-reference-agent-adoption-release-map.md
```

Then inspect the 12 new reference folders:

```text
openhands
aider
browser-use
smolagents
openai-agents-python
pydantic-ai
google-adk-python
semantic-kernel
llama-index
mastra
agno
haystack
```

## Files To Create

```text
docs/reference-agent-gap-audit.md
docs/reference-agent-adoption-matrix.md
docs/reference-agent-feature-deduplication.md
docs/reference-agent-licence-boundary.md
tests/reference_adoption/test_gap_matrix.py
```

## Audit Method

For every reference project, list:

- Capability.
- What it does.
- keprix equivalent if already covered.
- Existing prompt number if covered.
- Missing work if not covered.
- Whether it belongs in keprix, Petraclus, or a commercial connector.
- Risk level.
- Required approval policy.
- Required vault use.
- Required trace and artifact output.

Do not treat upstream names as product names. Rename capabilities in keprix language.

## Deduplication Rules

If a feature already exists in prompts 00 through 91:

- Do not create a second module.
- Add integration notes to the adoption matrix.
- Add tests or documentation only if the existing prompt lacks acceptance coverage.

If a feature overlaps but is stronger in the new reference:

- Extend the existing keprix module.
- Keep the existing route, CLI, and UI naming unless it is clearly wrong.

If a feature belongs to Petraclus:

- Mark it as excluded from keprix.
- Do not add it to keprix prompts.

If a feature is commercial-only:

- Mark it as connector-only.
- Do not imply it ships free inside keprix.

## Required Output Matrix Sections

Create these sections:

```text
1. Agent OS and engineering workspace
2. Git-native coding and patching
3. Browser automation and online task execution
4. Code-agent sandbox execution
5. Typed production agent runtime
6. Workflow runtime and lifecycle management
7. Enterprise plugin and interoperability layer
8. RAG, indexing, document agents, and retrieval pipelines
9. Interfaces, channels, and agent exposure
10. Observability, evals, traces, and improvement loops
11. Exclusions and product boundaries
12. Build order and dependency map
```

## Acceptance Criteria

- Every reference folder has at least one row in the matrix.
- Existing prompts 51 through 59 are treated as already planned, not duplicated.
- New prompts 107 through 119 are linked from the matrix.
- No copied upstream marketing language appears in the matrix.
- No Carina branding appears in keprix operator-facing copy.
- No em dash or en dash characters appear in new docs.

