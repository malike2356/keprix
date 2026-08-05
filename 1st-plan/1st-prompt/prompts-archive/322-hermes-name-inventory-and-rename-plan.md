# Keprix Prompt 322: Hermes Name Inventory and Rename Plan

## Purpose

Inventory all remaining Hermes names and classify each one before the full rename. Do not mechanically rename first; produce a safe rename map.

## Tasks

1. Create `docs/architecture/hermes-to-keprix-rename-inventory.md`.
2. Scan first-party files for:
   - `Hermes`
   - `hermes`
   - `HERMES`
   - `.hermes`
   - `hermes-agent`
   - `hermes_cli`
   - `ui-tui`
   - `tui_gateway`
3. Classify each occurrence:
   - rename now
   - compatibility alias
   - upstream reference
   - legal attribution
   - fixture or competitor reference
   - leave until package migration
4. Include a migration policy for state directories:
   - old `.hermes` paths must keep read compatibility
   - new state should use `.keprix`
   - migration must be idempotent
5. Include a migration policy for env vars:
   - old `HERMES_*` vars may be read as fallback
   - new `KEPRIX_*` vars win
   - warnings should be quiet by default and visible in doctor output

## Acceptance criteria

- No code is renamed in this prompt except docs and inventory scripts.
- The inventory includes Nix files, Docker files, docs, tests, package metadata, and CLI help.
- Legal attribution to Hermes Agent remains intact.

## Verification

```bash
rg -n "Hermes|hermes|HERMES|\\.hermes|hermes-agent|hermes_cli|ui-tui|tui_gateway" .
python3 scripts/fix-writing-style.py
```
