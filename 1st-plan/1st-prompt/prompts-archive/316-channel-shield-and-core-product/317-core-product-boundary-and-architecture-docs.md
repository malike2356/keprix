# Keprix Prompt 317: Core Product Boundary and Architecture Docs

## Purpose

Define the stable boundary between the Hermes-derived Keprix core engine and Keprix product modules. This is the foundation for every later rename and hardening prompt.

## Scope

Create or update architecture documentation that makes these boundaries explicit:

Core engine:

- `keprix.agent`
- `keprix.tui`
- `keprix.tools`
- `keprix.memory`
- `keprix.config`
- `keprix.sessions`
- CLI runtime and command dispatch
- Gateway primitives
- Provider routing
- Skill loading

Product layer:

- `keprix.agent_os`
- `keprix.channel_shield`
- `keprix.billing`
- `keprix.agent_apps`
- `keprix.backend`
- `keprix.ops`
- `keprix.scout`
- Product packs, built apps, domain workflows, admin dashboards

## Tasks

1. Add `docs/architecture/core-product-boundary.md`.
2. Add a short boundary summary to `README.md` and `docs/README.md`.
3. Add a developer rule to `AGENTS.md`: core must not import product modules directly.
4. Add a migration note explaining that Hermes-derived code is now Keprix core, not a product feature dumping ground.
5. Document sanctioned extension points:
   - command registry
   - route registry
   - tool registry
   - config registry
   - feature flag registry
   - product lifecycle hooks

## Acceptance criteria

- A new engineer can tell where to add a product feature without editing TUI, agent loop, memory internals, or tool executor.
- The docs explicitly say product modules may import core, but core must not import product modules.
- The docs explicitly say TUI changes must be generic unless a product-specific feature is exposed through slash commands or backend data.

## Verification

```bash
python3 scripts/fix-writing-style.py
rg "Hermes|hermes" docs README.md AGENTS.md
```

Existing Hermes references are allowed only where discussing upstream lineage, compatibility, or adoption.
