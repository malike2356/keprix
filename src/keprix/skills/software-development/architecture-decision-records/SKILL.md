---
name: architecture-decision-records
description: ADR template and playbook workflow for FORGE architecture decisions.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  keprix:
    tags: [forge, architecture, adr, design, playbook]
    related_skills: [architecture-diagram, plan]
---

# Architecture Decision Records

Document technology choices in ADR format via the playbook runtime.

## ADR Workflow

1. **Draft**; capture context, decision, and alternatives
2. **Review**; validate decision text is complete
3. **Publish**; render markdown and store in playbook state

## Template Sections

- Context
- Decision
- Consequences (positive and negative)
- Alternatives considered
- Implementation notes

## Usage

```python
from keprix.personas.forge.architect import ArchitectureDecision, ForgeArchitect

architect = ForgeArchitect(workspace_id="ws-1")
decision = ArchitectureDecision(
    title="Use FastAPI for HTTP layer",
    context="Need async API with OpenAPI docs",
    decision="Adopt FastAPI with Pydantic v2",
)
result = await architect.record_adr(decision)
```

Store ADRs in `playbook_state["adrs"]` for project history.
