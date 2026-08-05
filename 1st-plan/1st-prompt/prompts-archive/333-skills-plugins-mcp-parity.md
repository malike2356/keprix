# Keprix Prompt 333: Skills Plugins and MCP Parity

## Purpose

Match Hermes behavior for skills, plugins, MCP discovery, MCP execution, and gateway integrations while preserving Keprix product packs, marketplace, autonomous MCP, and connector governance.

## Preconditions

Complete Prompt 327 inventory first.

## Tasks

1. Compare Hermes and Keprix:
   - skill discovery
   - skill loading
   - skill priority
   - plugin discovery
   - plugin lifecycle
   - MCP config
   - MCP connection behavior
   - MCP tool schema handling
   - gateway exposure
2. Port missing Hermes behavior that improves reliability.
3. Preserve Keprix extensions:
   - product packs
   - marketplace catalog
   - autonomous MCP setup
   - connector-first policy
   - Scout governance
   - vault-backed credentials
4. Add tests for:
   - skill discovery
   - plugin discovery
   - MCP disabled
   - MCP enabled with mock server
   - malformed MCP schema
   - connector policy denied

## Acceptance criteria

- Skills and plugins behave like Hermes unless Keprix intentionally extends them.
- Product packs are product-layer assets, not core engine imports.
- MCP tool availability is stable and auditable.

## Verification

```bash
python -m pytest tests/skills tests/plugins tests/mcp tests/integration -q
python -m pytest tests/architecture -q
```
