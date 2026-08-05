# Keprix Prompt 329: Prompt Assembly and Context Parity

## Purpose

Match Hermes prompt assembly and context behavior while preserving Keprix layered prompts, persona engineering, product instructions, safety boundaries, and memory enrichments.

## Preconditions

Complete Prompt 327 inventory first.

## Tasks

1. Compare Hermes and Keprix prompt assembly:
   - system prompt layers
   - developer guidance
   - user message handling
   - tool descriptions
   - memory insertion
   - skill insertion
   - file context
   - workspace rules
   - compression summaries
2. Identify where Keprix has added product-specific instructions directly into generic core prompt assembly.
3. Move product-specific additions behind:
   - prompt layer registry
   - persona registry
   - product context provider
   - safety policy provider
4. Preserve Keprix improvements:
   - layered prompts
   - skill-first enforcement
   - persona prompts
   - guide enforcement
   - memory policy
   - Channel Shield safe content references
5. Add tests that compare prompt sections and ordering.

## Acceptance criteria

- Core prompt assembly is deterministic.
- Product prompt layers are registered, not hardcoded.
- Hermes-equivalent prompt sections are present unless Keprix intentionally improves them.
- Prompt tests cover ordering, duplicates, product extension insertion, and opt-out.

## Verification

```bash
python -m pytest tests/agent tests/memory tests/agent_apps -q
python -m pytest tests/architecture -q
```
