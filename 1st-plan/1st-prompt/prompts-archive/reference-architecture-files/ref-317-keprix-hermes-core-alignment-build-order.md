# Keprix Hermes Core Alignment Build Order

## Purpose

Make Keprix stable and solid by treating Hermes-derived runtime code as the engine and Keprix features as product extensions around it. This pack also performs the full Hermes-to-Keprix rename now, with compatibility preserved where needed.

## Current assessment

Keprix is a direct Hermes-derived fork. The core quality is valuable, but the codebase currently mixes product features into the same package as inherited runtime code. That creates risk when adopting upstream Hermes fixes, especially around the CLI, TUI, session runtime, provider routing, tools, memory, packaging, and Nix service code.

Hermes TUI should be treated as the stronger reference until a parity audit proves Keprix equals or exceeds it. Keprix TUI already has useful coverage and currently passes `tests/tui`, but this pack must compare behavior against the Hermes reference before declaring parity.

## Prompt order

1. `317-core-product-boundary-and-architecture-docs.md`
2. `318-core-product-import-boundary-tests.md`
3. `319-product-extension-registries-and-adapters.md`
4. `320-tui-freeze-and-hermes-parity-audit.md`
5. `321-packaged-install-parity-with-hermes.md`
6. `322-hermes-name-inventory-and-rename-plan.md`
7. `323-full-hermes-to-keprix-code-rename.md`
8. `324-nix-service-docker-and-docs-rename.md`
9. `325-upstream-adoption-workflow-hardening.md`
10. `326-release-hardening-and-solidness-verification.md`

## Non-negotiables

- Do not rewrite the runtime.
- Preserve working CLI and TUI behavior.
- Preserve compatibility aliases where old names are part of persisted config, generated files, package metadata, state directories, or upstream adoption logic.
- Product modules may import core. Core must not import product modules directly.
- New product features must enter through registries, adapters, config slots, feature flags, or API routes registered at the edge.
- No em dash, no en dash, no emojis.

## Verification target

At the end of the pack:

```bash
python -m pytest tests/tui -q
python -m pytest tests/cli tests/api tests/security -q
python -m pytest -q
pipx install '.[tui]'
keprix --help
keprix tui --help
keprix upstream --help
```

If full `pytest -q` is too broad for the local environment, document the exact failing tests and whether failures are unrelated to this pack.
