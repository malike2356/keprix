# Prompt 389 / 00: Overview and guardrails (capability mesh)

Status: COMPLETED 2026-08-04
Series: Keprix capability mesh  
Depends on: none  
Blocks: 390-402  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Workspace features, Keprix AI, and channels (especially Telegram) must form one spider web: every relevant module is linked to others, reachable by the agent, and operable from channels. Today UI/nav breadth exceeds toolset breadth. Without guardrails, teams invent parallel catalogs or bolt Telegram commands that bypass domain services.

## Goal

Adopt a single mesh architecture:

1. **Capability spine:** `tools.registry` + `_KEPRIX_CORE_TOOLS` / `keprix-telegram` (and other platforms).
2. **Object mesh:** shared durable IDs across modules (booking, event, contact, company, document, …).
3. **Capability graph:** feature nodes + edges for relatedness, tools, channel surfaces.
4. **Procedural overlay:** skills compose tools; Agent OS promote stays secondary.

## Naming

| Surface | Convention |
|---|---|
| Programme | capability mesh |
| Package (graph) | `src/keprix/capability_mesh/` (or `capabilities/`; pick one and stick) |
| Graph file | `capability_graph.yaml` (or `.json`) under package or `docs/architecture/` |
| Feature node id | match `ui_contract` nav ids where possible (`vical`, `calendar`, `contacts`, …) |
| Docs | `docs/features/capability-mesh.md` + keep updating `agent-surface-access.md` |
| CI gate | `scripts/check-capability-mesh.sh` (prompt 02/03/13) |

## Integration contract

1. Channel reachability = tool (or skill calling tools) in the platform toolset. UI alone is not enough.
2. Channel Shield is ingress safety, not the feature router.
3. Domain services remain authority; tools and HTTP wrap the same code paths (viCal pattern).
4. Cross-feature hops use object IDs + graph edges, not scrape HTML.

## Must-haves (this prompt)

1. Record the architecture in this series README (already) and seed `docs/features/capability-mesh.md` outline.
2. Explicit non-goals and "Companies House path" as the tool exposure template.
3. Pointers to pilot vertical (07/08): viCal + calendar + contacts on Telegram.

## Acceptance

- [ ] Implementing agent can start 01 without inventing a second bus.
- [ ] `docs/features/capability-mesh.md` exists with spine/object/graph/skills sections.
- [ ] Writing-style clean on new copy.
