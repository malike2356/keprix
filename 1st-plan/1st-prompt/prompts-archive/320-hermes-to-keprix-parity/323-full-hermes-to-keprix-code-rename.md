# Keprix Prompt 323: Full Hermes to Keprix Code Rename

## Purpose

Perform the full first-party Hermes-to-Keprix rename using the inventory from Prompt 322, while preserving compatibility aliases.

## Preconditions

Complete Prompt 322 first.

## Tasks

1. Rename first-party module, class, function, config, env, and display names classified as `rename now`.
2. Preserve legal attribution and upstream references.
3. Add compatibility shims where old names may exist in:
   - config files
   - state directories
   - env vars
   - CLI aliases
   - persisted sessions
   - install paths
4. Add state migration:
   - `.hermes` to `.keprix`
   - old path remains readable
   - new writes go to `.keprix`
5. Add env migration:
   - read `KEPRIX_*` first
   - fall back to `HERMES_*`
   - expose deprecations in `keprix doctor`
6. Update tests and fixtures only when they are first-party Keprix behavior, not upstream snapshots.

## Do not rename

- MIT license attribution.
- Docs that explicitly say Keprix derives from Hermes Agent.
- Competitor research snapshots.
- Upstream adoption references.
- Compatibility test fixtures that intentionally use old names.

## Acceptance criteria

- New user-facing output says Keprix.
- `keprix doctor` reports old Hermes env or state usage as compatibility, not failure.
- Old config still loads.
- New config writes Keprix names.

## Verification

```bash
python -m pytest tests/cli tests/config tests/tui tests/api -q
python -m pytest tests/architecture/test_core_product_boundaries.py -q
keprix --help
keprix doctor
rg -n "Hermes|hermes|HERMES|\\.hermes|hermes-agent|hermes_cli|ui-tui|tui_gateway" src docs tests pyproject.toml
```

Every remaining match must be explained by the Prompt 322 inventory.
