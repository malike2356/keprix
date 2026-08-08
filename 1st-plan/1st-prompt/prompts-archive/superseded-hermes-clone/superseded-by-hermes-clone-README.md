# Superseded by Hermes Clone

These build prompts are archived because their primary deliverable was a verbatim
Hermes-to-Keprix port. That work landed in foundation commit `10c60d0`
(`feat(foundation): adopt Hermes as Keprix backbone, complete rename`).

Do not re-run these prompts to rebuild the spine. Use them only as reference for
what was cloned and what still needs Keprix-specific adaptation elsewhere.

Reference agent clones (for gap analysis when extending beyond Hermes) live at
`planning/agents-to-adopt/` (absolute: `/opt/lampp/htdocs/verlox/keprix/planning/agents-to-adopt/`).

## Archived prompts

| Prompt | Hermes source now in `src/keprix/` |
| --- | --- |
| 03 Core agent engine | `agent/`, `run_agent.py`, conversation loop, tool dispatch |
| 04 LLM providers and routing | `providers/`, provider adapters under `agent/` |
| 05 Tools and terminal | `tools/`, `toolsets.py`, LSP, tool guardrails |
| 07 Skills and plugins | `skills/`, `optional-skills/`, `plugins/`, `agent/skill_*.py` |
| 13 Messaging gateway | `gateway/`, platform adapters, slash command gateway |
| 15 Cron automation | `cron/` |
| 17 MCP, ACP, integrations | `acp_adapter/`, `acp_registry/`, `optional-mcps/` |
| 43 Coding posture detection | `agent/coding_context.py` |

## Still active (not superseded)

These related prompts remain in `pending-prompts/` because they add Keprix-only
layers on top of the cloned spine:

- **06** Memory and RAG: pgvector, ChromaDB, episodic store (Hermes Layer 1 only)
- **08-12** Workspace, vault, email, contacts (Carina/Odysseus patterns)
- **18-22** New FastAPI surface and Next.js UI (Hermes web/TUI intentionally dropped)
- **23** Unified slash-command registry for Next.js and new API
- **40** Final rebrand and release sweep (initial rename done; full sweep later)
- **45-46** OpenClaw ambient room and wake-word patterns (not in Hermes clone)

## Deliberately removed from clone

- `web/` and `tui_gateway/` (replaced by Next.js prompts 116-118, 136-137)
