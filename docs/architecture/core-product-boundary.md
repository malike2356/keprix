# Core and product boundary

Keprix uses a stable core engine with product modules around it. The core is the part that should stay close to the Hermes-derived runtime quality: agent loop, tool dispatch, prompt assembly, sessions, memory, provider routing, skills, plugins, MCP, CLI, gateway primitives, and TUI runtime.

The product layer is where Keprix differentiates: Agent OS, Channel Shield, billing, Scout governance, agent apps, admin APIs, product packs, workflows, dashboards, and hosted product surfaces.

This boundary exists to keep Keprix stable. Product features can grow quickly without making the inherited runtime fragile.

## Core engine

Core code is allowed to depend on small shared utilities, registries, and interfaces. It must not import product modules directly.

Core areas include:

- `keprix.agent`
- `keprix.tui`
- `keprix.tools`
- `keprix.memory`
- `keprix.config`
- CLI runtime and command dispatch
- Gateway primitives
- Provider routing
- Skill loading
- Session and checkpoint runtime

Core code should answer generic runtime questions:

- How does a turn run?
- How are tools selected and called?
- How are prompts assembled?
- How are sessions resumed?
- How are streams, retries, and provider failures handled?
- How does the TUI communicate with the agent runtime?

## Product layer

Product modules may import core modules. Product modules must extend the core through registries, adapters, config, feature flags, or hooks.

Product areas include:

- `keprix.agent_os`
- `keprix.channel_shield`
- `keprix.billing`
- `keprix.agent_apps`
- `keprix.backend`
- `keprix.ops`
- `keprix.scout`
- Product packs
- Built apps
- Domain workflows
- Admin dashboards

Product code should answer business and product questions:

- Which features are enabled for this operator?
- Which product pack owns this workflow?
- Which billing gate applies?
- Which governance signal is emitted?
- Which dashboard or admin route exposes this capability?

## Allowed extension points

Use explicit extension points instead of direct imports from core into product modules.

### Command registry

Register product commands at the CLI edge. Core command dispatch may load the registry, but it must not import concrete product command modules directly.

### Route registry

Register product API routes from the API composition layer. Core gateway primitives should not know product route implementations.

### Tool registry

Register product tools through the tool registry. The generic tool executor should handle schemas, permissions, execution, audit, and result formatting without importing product services.

### Config registry

Register product config sections with typed defaults and validation. Core config loading should stay generic.

### Feature flag registry

Register product flags in one place. Core can ask whether a generic capability is enabled, but product modules own product-specific flag meaning.

### Product hooks

Use product hooks for side effects around turns and tool calls:

- before turn
- after turn
- before tool call
- after tool call
- on session created
- on session resumed
- on stream event

Hooks must be optional. If a product module is disabled or missing, core runtime should continue.

## TUI rule

`keprix.tui` is core. Product features may expose data or commands to the TUI through APIs and slash commands, but product modules must not be imported into the TUI runtime.

TUI changes should be generic unless they are only displaying data returned by a product API. The TUI should keep Keprix UI and brand identity. Hermes can be used as a behavior and interaction-quality reference, not as a visual surface to copy.

## Import rule

Allowed:

```python
from keprix.agent import conversation_loop
from keprix.registries.product_hooks import run_after_turn_hooks
from keprix.agent_os.routes import router
```

Not allowed inside core modules:

```python
from keprix.agent_os import run_ledger
from keprix.channel_shield import scanner
from keprix.billing import entitlement_gate
```

Instead, product modules register hooks or adapters:

```python
register_after_turn_hook(agent_os_after_turn)
register_before_tool_hook(channel_shield_before_tool)
register_entitlement_provider(billing_entitlements)
```

## Compatibility

Some Hermes names may remain for compatibility, upstream attribution, migration, or comparison. New user-facing Keprix behavior should use Keprix naming. Old state or env names may be accepted as fallbacks, but new writes should prefer Keprix names.

## Review checklist

Before merging a change:

- Does a core module import a product module?
- Could this be a registry entry, adapter, or hook?
- Does this change TUI behavior for every user or only one product?
- Does this preserve Agent OS, Channel Shield, Scout, billing, and app extensions?
- Does the change keep packaged install behavior simple?
- Does the change preserve existing tests for core and product modules?
