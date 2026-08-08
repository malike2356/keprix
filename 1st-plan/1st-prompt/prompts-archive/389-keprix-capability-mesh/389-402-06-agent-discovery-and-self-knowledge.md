# Prompt 395 / 06: Agent discovery and self-knowledge from graph

Status: COMPLETED 2026-08-04
Series: Keprix capability mesh  
Depends on: 390 / 01, 391 / 02  
Blocks: 396, 402  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Tools in the set are not enough if the model cannot discover related capabilities. Self-knowledge and tool_search must reflect the mesh.

## Goal

Feed capability graph into agent discoverability surfaces.

## Baseline

| Piece | Path |
|---|---|
| tool_search | `tools/tool_search.py` |
| Self-knowledge / RAG | memory/self-knowledge paths under `keprix` |
| Personas | `personas/registry.py` |

## Must-haves

1. Generate or sync a short "what can I do / what links to what" doc from the graph into self-knowledge corpus (or equivalent teachable artifact).
2. Ensure mesh docs are listed in agent-facing surface docs.
3. Optional: `tool_search` boost or synonyms for pilot tools (`book`, `vical`, `slot`, `contact`).
4. Test that graph export text includes pilot nodes once seeded.

## Nice-to-haves

1. Slash `/capabilities` summarizing channel-ready nodes for the current platform.

## Acceptance

- [ ] Regenerating graph updates the discovery artifact.
- [ ] Documented how operators refresh self-knowledge after graph edits.
