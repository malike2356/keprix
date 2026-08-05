# Keprix Prompt 318: Core Product Import Boundary Tests

## Purpose

Add automated tests that prevent product modules from leaking into core runtime areas.

## Tasks

1. Create `tests/architecture/test_core_product_boundaries.py`.
2. Define core package prefixes:
   - `keprix.agent`
   - `keprix.tui`
   - `keprix.tools`
   - `keprix.memory`
   - `keprix.config`
   - core CLI entry modules
3. Define product package prefixes:
   - `keprix.agent_os`
   - `keprix.channel_shield`
   - `keprix.billing`
   - `keprix.agent_apps`
   - `keprix.backend`
   - `keprix.ops`
   - `keprix.scout`
4. Parse imports using `ast`, not string grep.
5. Fail if a core module imports a product module directly.
6. Allow a small explicit exception list with comments and expiry notes.

## Required policy

- `keprix.tui` must not import product modules.
- `keprix.agent` must not import product modules directly.
- Product modules may import core modules.
- Product code must register with core through registries or adapters.

## Acceptance criteria

- The test fails if `keprix.tui.app` imports `keprix.billing`.
- The test fails if `keprix.agent.conversation_loop` imports `keprix.channel_shield`.
- The test passes for product modules importing `keprix.agent` types or utilities.
- Any exception is documented inline with a removal target.

## Verification

```bash
python -m pytest tests/architecture/test_core_product_boundaries.py -q
python -m pytest tests/tui -q
```
