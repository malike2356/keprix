# Reversible plugin lifecycle

**Status:** Implemented (prompt 769, 2026-09-20)
**Package:** `keprix.plugin_lifecycle`
**Depends on:** capability seams (`keprix.seams`, prompt 768)

## Intent

Hot enable/disable must be **reversible**. Unload undoes tool schemas, prompt
sections (by section id), MCP server bindings, and seam Provider contributions
so the agent loop and UI do not keep orphaned capabilities.

Steal the DeepSeek Harness reversible-plugin *idea*. Stay on Keprix's Python
plugin loader. Do not import Cordis.

## What is tracked (per plugin id)

| Effect | Recorded in ledger | Unload action |
| --- | --- | --- |
| Tools | yes | `tools.registry.deregister` |
| Hooks / middleware | yes (callback identity) | remove from PluginManager lists |
| Slash / CLI commands | yes | pop from manager maps |
| Skills / aux tasks | yes | pop |
| Prompt sections | yes (by `section_id`) | `clear_prompt_section` |
| MCP servers | yes | `unregister_server_runtime` |
| Seam Providers | yes | `SeamRegistry.unregister` |
| Platforms | yes | drop name; unregister if API exists |

## Operator commands

```bash
keprix plugins enable <name>    # config + hot mount in current process
keprix plugins disable <name>   # config + hot unmount (no file delete)
```

Programmatic:

```python
from keprix.plugin_lifecycle import enable_plugin_hot, disable_plugin_hot, list_audit_events

enable_plugin_hot("observability/nemo_relay", who="ops")
disable_plugin_hot("observability/nemo_relay", who="ops")
list_audit_events(limit=20)
```

Disable does **not** delete plugin files. Only runtime effects are reversed.

## Plugin author APIs (PluginContext)

```python
def register(ctx):
    ctx.register_tool(...)
    ctx.register_prompt_section("myplugin.banner", "...")
    ctx.register_mcp_server("filesystem", {...})   # optional
    ctx.register_seam_provider("fs", MyFsProvider())  # optional
```

Prompt injectors must use **section ids**, not free-floating string appends that
cannot be reversed.

## Soft Wall / Channel Shield

Unload and remount do not bypass Soft Wall. Seam Providers remain wrapable with
`PolicyWrappedShell` / vault floors / Channel Shield scheme gates. After reload,
hardline still blocks catastrophic shell commands.

## Non-goals

- Playbooks, CRM, billing, Document Vault, Channel Shield are first-class OS
  modules, not plugins, and are outside this lifecycle.
- No Cordis / TypeScript rewrite.
- No remote marketplace or unsigned auto-install.
- Mutation Engine mount mapping is prompt 773.

## Restart case

If no PluginManager is live in the process (CLI config-only path before
discovery), enable/disable still update `config.yaml` and take effect on the
next session. When a manager is live, mount/unmount is in-process.

## Related

- `docs/architecture/capability-seams.md`
- `keprix_cli/plugins.py` (`PluginManager.mount_plugin` / `unmount_plugin`)
- `keprix plugins enable|disable`
