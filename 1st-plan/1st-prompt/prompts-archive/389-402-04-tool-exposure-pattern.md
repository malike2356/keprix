# Prompt 393 / 04: Tool exposure pattern (Companies House path)

Status: COMPLETED 2026-08-04
Series: Keprix capability mesh  
Depends on: 389 / 00  
Blocks: 396, 399, 400  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Every new channel-reachable feature must follow one recipe so Telegram parity stays mechanical.

## Goal

Document and lightly codify the Companies House exposure pattern as a reusable checklist + helper stubs if useful.

## Baseline

| Piece | Path |
|---|---|
| CH tools in core | `toolsets.py` |
| Registry | `tools/registry.py` |
| Platform tools | `keprix_cli/tools_config.py` |
| Surface docs | `docs/features/agent-surface-access.md` |

## Must-haves

1. Step-by-step recipe in `docs/features/capability-mesh.md` and/or `docs/features/agent-surface-access.md`:
   - implement domain service
   - `registry.register` with `check_fn`
   - add to named toolset and `_KEPRIX_CORE_TOOLS` when channel-default
   - update capability graph node
   - update surface-access docs
   - pytest tool invoke smoke
2. Reference file list for a "tool module" layout matching existing conventions.
3. Explicit note: opt-in toolsets for dangerous/admin tools; webhook-safe subset stays narrow.

## Acceptance

- [ ] Recipe is copy-pasteable for viCal tools in 07.
- [ ] Docs updated; no secret values.
