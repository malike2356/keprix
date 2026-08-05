# Keprix Prompt 325: Upstream Adoption Workflow Hardening

## Purpose

Keep the ability to adopt Hermes improvements without making Keprix a messy fork again.

## Tasks

1. Review `keprix upstream` commands.
2. Ensure upstream adoption reports separate:
   - generic core improvements
   - TUI improvements
   - product-layer conflicts
   - rename conflicts
3. Add an upstream patch intake checklist:
   - Does this modify core?
   - Does this modify product layer?
   - Does it introduce Hermes names?
   - Does it affect install packaging?
   - Does it affect TUI behavior?
4. Add tests or snapshots for upstream adoption prompt generation.
5. Add docs: `docs/architecture/upstream-adoption-policy.md`.

## Policy

Generic runtime fixes can enter core.

Product-specific Keprix features must not be backported into core.

Hermes names from upstream patches must be translated through the rename map unless legal attribution or upstream reference requires the original name.

## Acceptance criteria

- `keprix upstream --help` works.
- Upstream adoption docs reference the new core/product boundary.
- Generated prompts tell agents where the change belongs.

## Verification

```bash
keprix upstream --help
python -m pytest tests/upgrade tests/cli -q
python3 scripts/fix-writing-style.py
```
