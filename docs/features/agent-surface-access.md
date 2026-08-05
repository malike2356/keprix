# Agent surface access (Telegram, Web UI, workspace)

Status: living notes (updated with Companies House wiring 2026-08-04; capability mesh programme 389-402)

## Short answers

| Question | Answer |
| --- | --- |
| Menu + GUI for Companies House? | Yes: Research nav → **Companies House** → `/companies-house` |
| Can the AI search CH from Telegram? | Yes **after** tools are in core toolsets and the Telegram gateway is running with the same bot token config |
| Does the AI know/use every feature with full R/W everywhere? | **No.** It gets a large default toolset (files, terminal, web, memory, CH, …) under ACL, egress, approvals, and sandbox; not unbounded root access to every product UI |

## Surfaces

1. **Web UI chat** (`platform=web_ui`): toolsets resolved like CLI so Web UI is not an empty tool platform.
2. **Telegram / Discord / WhatsApp / …**: `platform_toolsets` default to `keprix-<platform>` which expands from `_KEPRIX_CORE_TOOLS`.
3. **Companies House tools**: `search:companies_house`, `get:company_profile` (toolset `companies_house`).

## Gaps to expect

- Gateway must be up for Telegram.
- Dangerous shell / mutation / pack install stay gated.
- Admin-only HTTP dashboards are not all exposed as agent tools.
- Tool search may defer rare tools until retrieved.

## Capability mesh

Cross-feature relatedness and channel readiness are tracked in `docs/features/capability-mesh.md` and `src/keprix/capability_mesh/capability_graph.yaml`. Do not invent a second tool bus; extend `_KEPRIX_CORE_TOOLS` / platform toolsets.

**Companies House path (recipe):** domain service -> `registry.register` + `check_fn` -> named toolset + `_KEPRIX_CORE_TOOLS` -> graph node `wired` + telegram surface -> docs + smoke. See capability-mesh.md for the full checklist.

Programme: archived under `1st-plan/1st-prompt/prompts-archive/389-402-*.md` (pointer: `pending-prompts/keprix-capability-mesh/README.md`).
Audit: `PYTHONPATH=src python3 -m keprix.capability_mesh audit --write`. Discoverability: `python3 -m keprix.capability_mesh discovery --write` (also ingested via self-knowledge).

Pilot tools in core toolsets (Telegram/Discord/Slack/CLI inherit): `vical_*`, `calendar_list_events`, `contacts_search`, `contacts_get`. Slash: `/slots`, `/bookings`.

