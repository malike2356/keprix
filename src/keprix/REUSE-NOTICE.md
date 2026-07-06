# Keprix - RESEARCH ONLY

**Source:** Nous Research - Keprix
**Status:** Reference material. Nothing in this directory ships in Carina verbatim.

Read `../REUSE-NOTICE.md` for the full policy.

---

## Keprix-specific vocabulary that must NOT appear in Carina production code

| Keprix term | Carina must replace with |
|---|---|
| `keprix` (CLI name) | `carina` |
| `KEPRIX_HOME` | `CARINA_HOME` |
| `~/.keprix/` | `~/.carina/` |
| Skin names: ares, default, mono, slate | Carina's own skin names (see gap-09/04) |
| "KawaiiSpinner" | (unnamed) - implement spinner frames via config without this label |
| "Skill Curator" (as a named feature) | Implement the behavior; give it a Carina name |
| "Kanban" as a feature label shown to users | Evaluate; "Task Board" may be clearer |
| "Keprix Profile" / profile subcommand names | Use `carina workspace` or `carina profile` equivalents |
| `keprix kanban init` / `assign` / `block` etc. | Map to `carina task <verb>` equivalents |
| "Footprint Ladder" (internal term) | Not exposed to users; can keep as internal comment |
| "Delegation" as a user-facing concept | Use "Agent Tasks" or Carina's own terminology |
| "Skin engine" as a feature label | Call it "Themes" or "Appearance" in Carina's UI |
| "Auxiliary model" config key name | Use `taskModels` or `specialistModels` in Carina config |
| Cron YAML key names (workdir, context_from, no_agent, etc.) | Evaluate each; rename if they are user-visible |
| `--now` flag name | Keep or rename; but not because Keprix uses it |

---

## What we are adopting from Keprix (behavior, not language)

- Prompt caching invariant: freeze system prompt per conversation
- Skill lifecycle management: usage tracking, background archiving
- Per-task auxiliary model routing
- SQLite-backed multi-agent task queue
- Cron: script injection, chaining, script-only mode
- Delegation depth limits
- Multi-profile isolation
- Data-driven terminal theming
- ACP adapter for IDE integration
- FTS5 session search with LLM summarization
