# Capability seams (Definition / Provider / Consumer)

**Status:** Implemented (prompt 768, 2026-09-20)
**Package:** `keprix.seams`
**Related:** Soft Wall (`tools/approval.py`), Channel Shield (`keprix.channel_shield`),
vault floors, execution environments (`tools/environments/`), tool registry
(`tools/registry.py`)

## Intent

Steal the DeepSeek Harness / Cordis *idea* of capability seams, not the runtime.
Keprix keeps its Python agent OS. One Provider swap should move related tools
without rewriting Consumers.

## Three roles

| Role | Meaning in Keprix |
| --- | --- |
| **Definition** | Protocol / contract: method shapes, error model, related tool schema metadata (`keprix.seams.definitions`) |
| **Provider** | Concrete implementation (`fs.local`, `fs.sandboxed`, `shell.local`, …) |
| **Consumer** | Agent loop, skills, MCP adapters, UI helpers that call only the Definition (`keprix.seams.consumers`) |

A seam is all three. A Provider alone is not a seam.

## The six seams

| Seam id | Capability | Default Provider | Related tools (metadata) |
| --- | --- | --- | --- |
| `fs` | Filesystem | `policy:fs.local` (vault-floor wrapped) | read_file, write_file, search_files, list_dir, patch |
| `shell` | Command execution | `policy:shell.local` (hardline Soft Wall wrapped) | terminal, execute_code |
| `memory` | Durable / session memory | `memory.default` (workspace-scoped) | memory, conversation_search |
| `llm` | Model routing / completion | `llm.default` (route resolve; complete is stub) | (routing, not a single tool) |
| `subagent` | Spawn / delegate | `subagent.default` | delegate_task |
| `web` | HTTP fetch / search / browse | `policy:web.default` (scheme Channel Shield) | web_search, web_extract, browser_navigate |

## Map to current Keprix code

| Seam | Already exists | Gap closed by 768 |
| --- | --- | --- |
| `fs` / `shell` | `tools/environments/*` + `terminal_tool` / `file_tools` | Named Definition + registry + sandboxed alternate + policy wrappers |
| `memory` | `tools/memory_tool.py`, RAG / self-knowledge | Workspace-scoped Provider contract |
| `llm` | provider profiles, `keprix_cli` model config, agent loop | Route Definition; live complete stays in agent loop |
| `subagent` | `tools/delegate_tool.py` | Describe / spawn contract pointing at delegate_task |
| `web` | `tools/web_tools.py`, browser tools, BYOK backends | Search/fetch Definition + scheme gate |

`tools.registry` remains the tool schema/handler registry. `keprix.seams` does
**not** invent a second parallel tool registry; it names which Provider backs
each capability so related tools can move together.

`keprix.capability_mesh` (nav / DoD graph) is a different concept. Do not merge
them.

## Soft Wall / Channel Shield / vault

Policy wrappers sit **around** Providers:

- `PolicyWrappedShell` → hardline Soft Wall (`detect_hardline_command`)
- `PolicyWrappedFs` → vault / credential path floors
- `PolicyWrappedWeb` → Channel Shield scheme denials (`file:`, `javascript:`, `data:`)

Consumers still call `get_shell()` / `get_fs()` / `get_web()`. Gates are not
alternate consumers that skip the seam.

Full Channel Shield, CRM Soft Wall approvals, and Document Vault remain
first-class product modules.

## Provider swap demo

```python
from keprix.seams import ensure_default_seams, get_fs, get_seam_registry

ensure_default_seams(sandbox_root="/tmp/keprix-seam-demo", force=True)
reg = get_seam_registry()
reg.set_active("fs", "policy:fs.sandboxed")
fs = get_fs()  # Definition only; no consumer code change
fs.write_text("note.txt", "hello")
assert "note.txt" in fs.list_dir(".")
```

Swapping `fs.local` → `fs.sandboxed` (or their `policy:` wrappers) changes
behaviour without editing the consumer.

## Non-goals (hard)

1. No Cordis / TypeScript rewrite of Keprix.
2. No "everything must be a plugin" for Playbooks, CRM, billing, Document Vault,
   or Channel Shield.
3. No production dependency on `deepseek-harness` or Cordis packages.
4. No star-count or hype as maturity evidence.
5. Do not weaken Soft Wall, four-eyes, Channel Shield, vault floors, or tenant RLS.

## API cheat sheet

```python
from keprix.seams import (
    ensure_default_seams,
    get_fs, get_shell, get_memory, get_llm, get_subagent, get_web,
    get_seam_registry,
)

ensure_default_seams()
get_seam_registry().snapshot()
```

## Follow-ons

- 769: reversible plugin lifecycle (unload undoes registrations including seam Providers)
- 771: declarative capability packs that select Providers
- 773: Mutation Engine proposals mapped to mount/unmount
