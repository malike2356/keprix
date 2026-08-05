# Keprix Prompt 319: Product Extension Registries and Adapters

## Purpose

Move the worst direct product imports behind registries and adapters so the core can remain stable while Keprix features keep working.

## Tasks

1. Add a `keprix/registries/` package if it does not already exist.
2. Add these registry modules:
   - `product_commands.py`
   - `product_routes.py`
   - `product_tools.py`
   - `product_config.py`
   - `product_hooks.py`
3. Each registry must be small, typed, and dependency-light.
4. Core code may import registries.
5. Product modules register handlers through registry calls.
6. Move direct product imports found by Prompt 318 into adapters.

## Registry shape

Prefer simple explicit APIs:

```python
register_command(name: str, handler: CommandHandler, *, product: str) -> None
iter_commands() -> list[RegisteredCommand]
```

Do not introduce a heavy plugin framework in this prompt.

## Priority migration targets

1. CLI command list entries that pull in product modules too early.
2. API route mounting that imports product modules during core startup.
3. Tool registration that imports product-specific services in core.
4. TUI slash fallthrough paths that know product internals.

## Acceptance criteria

- Core import boundary tests pass.
- Existing CLI commands still show in help.
- Existing product routes still mount.
- TUI behavior remains unchanged.

## Verification

```bash
python -m pytest tests/architecture/test_core_product_boundaries.py -q
python -m pytest tests/cli tests/api tests/tui -q
keprix --help
keprix channel-shield --help
keprix agent-os --help
```
