# Prompt 391 / 02: Feature Definition of Done (mesh contract)

Status: COMPLETED 2026-08-04
Series: Keprix capability mesh  
Depends on: 390 / 01  
Blocks: 392, 393, 402  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Without a contract, new UI pages ship without tools/channel edges and the spider web frays.

## Goal

Codify and enforce (where practical) a Definition of Done for workspace features that should be "neurally linked."

## Must-haves

1. Written DoD checklist in `docs/features/capability-mesh.md`:
   - Domain service / API
   - UI (if human-facing)
   - Agent tool(s) registered
   - Core or documented opt-in toolset membership for Telegram
   - Capability graph node + edges with ID fields
   - Self-knowledge / discoverability note
   - Tests + channel smoke note
2. Script or pytest helper that can assert: for nodes marked `required_channel=telegram`, tools listed exist in registry and appear in `keprix-telegram` expansion (or explicitly documented exception).
3. Template snippet for future prompts: "Mesh DoD" section.

## Nice-to-haves

1. CI job soft-fail then hard-fail after pilot (document soak).

## Acceptance

- [ ] DoD documented.
- [ ] Automated check covers tool existence for seeded `wired` telegram nodes (or lists intentional exceptions).
- [ ] Companies House and viCal called out as reference implementations (CH wired; viCal tools may still be gap until 07).
