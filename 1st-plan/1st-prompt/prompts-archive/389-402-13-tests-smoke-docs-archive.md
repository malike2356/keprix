# Prompt 402 / 13: Tests, smoke, docs, archive

Status: COMPLETED 2026-08-04
Series: Keprix capability mesh  
Depends on: 389-401 minimum for pilot path (07/08); rollups may be partial with owner note  
Writing style: plain ASCII only (no em/en dashes, no emoji).

## Why this exists

Programme is only done when the mesh is evidenced, documented, and prompts archived.

## Goal

Harden tests, write smoke script, finalize docs, archive prompts.

## Must-haves

1. Pytest matrix:
   - graph load/neighbors
   - audit / DoD checks
   - pilot tools
   - ID resolve helpers
   - toolset membership regression
   - reminder outbound mock (if 08 landed)
2. Smoke doc section: Telegram gateway up -> book via chat/slash -> see `/calendar` -> reminder outbound (if configured).
3. Ops flags listed in `capability-mesh.md` and `agent-surface-access.md`.
4. Queue hygiene: mark COMPLETED, move to `prompts-archive/`, update pending README + series pointer + `ref-389-*.md`.
5. Writing-style scan on touched first-party files.

## Acceptance

- [ ] Documented pytest command green with evidence note (no secrets).
- [ ] Pilot Telegram path documented as default proof of mesh.
- [ ] Remaining rollup gaps explicitly deferred if any.
