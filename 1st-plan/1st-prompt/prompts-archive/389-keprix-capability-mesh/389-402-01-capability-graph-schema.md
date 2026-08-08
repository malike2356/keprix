# Prompt 390 / 01: Capability graph schema and loader

Status: COMPLETED 2026-08-04
Series: Keprix capability mesh  
Depends on: 389 / 00  
Blocks: 391, 392, 395, 398, 399+  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Relatedness cannot be N×N hardcoded imports. A small graph of feature nodes and edges is the synapse layer for UI deep links, agent discovery, and gap audits.

## Goal

Ship a versioned capability graph schema + loader + query helpers.

## Baseline

| Piece | Path |
|---|---|
| Nav ids | `ui_contract/navigation.py` |
| Tool names | `toolsets.py` `_KEPRIX_CORE_TOOLS`, `TOOLSETS` |
| Upstream keywords (doctrine only) | `upstream/capability_registry.yaml` (do not treat as runtime ACL) |

## Must-haves

1. Schema fields per **node**: `id`, `label`, `nav_id` (optional), `tools[]`, `channel_surfaces[]` (`web_ui`, `telegram`, `cli`, …), `object_types[]`, `status` (`wired` / `partial` / `ui_only`).
2. Schema fields per **edge**: `from`, `to`, `relation` (`creates`, `references`, `enriches`, `schedules`, …), `via_id_field` (e.g. `workspace_event_id`).
3. Load from YAML/JSON checked into repo; Python API: `get_node`, `neighbors`, `tools_for`, `channel_ready`.
4. Seed v0 covering at least: `home`, `chat`, `calendar`, `vical`, `contacts`, `companies-house`, `memory`, `playbooks`, `cron`, `vault` (honest status).
5. Unit tests for load + neighbor queries + invalid edge detection.

## Nice-to-haves

1. Graph export for docs Mermaid generation.
2. Optional HTTP `GET /api/capabilities/graph` (auth) for UI later.

## Acceptance

- [ ] Loader rejects duplicate node ids and dangling edges.
- [ ] Seed graph checked in; tests green.
- [ ] Docs describe how to add a node when shipping a feature.
