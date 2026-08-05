# Keprix Prompt 175: Productivity Integrations - Skills, Routing, and Playbook

## Purpose

Complete the **skills path** for Notion and Trello and teach the agent **which path to use**
(MCP live tools vs RAG search vs skill/terminal API). Operators get a productivity integration
surface in the workspace without reading architecture docs.

Read reference 171. Requires prompt **172**; works alongside 173-174.

---

## Dependencies

- `src/keprix/skills/productivity/notion/SKILL.md` (exists).
- `src/keprix/skills/productivity/airtable/SKILL.md` (pattern for new trello skill).
- Skills registry / `keprix skills config` machinery.
- Optional: `src/keprix/playbook/` for example playbook YAML.

---

## What to build

### 1. New skill: `trello`

**`src/keprix/skills/productivity/trello/SKILL.md`** (NEW)

Mirror `airtable` skill structure:

```yaml
---
name: trello
description: Trello REST API via curl. Boards, lists, cards CRUD.
version: 1.0.0
author: community
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  env_vars: [TRELLO_API_KEY, TRELLO_TOKEN]
  commands: [curl]
metadata:
  keprix:
    tags: [Trello, Productivity, Kanban, API, Project Management]
    homepage: https://developer.atlassian.com/cloud/trello/rest/
    related_skills: [notion, project-tracking]
---
```

Content sections (implement fully, not outline):

1. Prerequisites: Power-Up admin URL, how to generate key + token.
2. API basics: `https://api.trello.com/1/...?key=$TRELLO_API_KEY&token=$TRELLO_TOKEN`
3. Examples via `terminal` tool:
   - `GET /members/me/boards`
   - `GET /boards/{id}/lists`
   - `GET /lists/{id}/cards`
   - `POST /cards` (name, idList)
   - `PUT /cards/{id}` (move list, due date)
4. Rate limits and error handling.
5. **When to use this skill vs MCP:** prefer MCP when `mcp_trello_*` tools are available.

**`src/keprix/skills/productivity/trello/references/rest-endpoints.md`** (NEW, concise reference table).

Register skill in the same manifest/index file other productivity skills use (grep for
`notion` skill registration and follow exactly).

### 2. Routing skill: `productivity-integrations`

**`src/keprix/skills/productivity/productivity-integrations/SKILL.md`** (NEW)

Teach the agent decision tree:

```
User wants live edit of Notion/Trello
  -> If MCP server connected (mcp_notion_* / mcp_trello_*): use MCP tools
  -> Else if credentials in env: suggest /admin/mcp or use trello/notion skill

User wants search across Notion docs already indexed
  -> Use rag pipeline query tools (name the actual tool from rag_pipeline)

User wants one-off read without MCP installed
  -> notion skill or trello skill via terminal/curl

User wants automation without OAuth browser
  -> notion-token MCP or NOTION_TOKEN + RAG ingest
```

Include explicit tool name prefixes: `mcp_notion_`, `mcp_trello_`, `mcp_notion_token_` if server
named `notion-token`.

### 3. Default skill profile

If Keprix has a **productivity** or **default** skill profile in config:

- Enable `notion`, `trello`, `productivity-integrations` by default for new installs.
- Do not enable if project uses opt-in-only; instead add to `cli-config.yaml.example` commented block.

Document in skill config example:

```yaml
skills:
  enabled:
    - notion
    - trello
    - productivity-integrations
```

### 4. Workspace integrations card

**Option A (preferred):** extend `/admin/mcp` with subsection **Also available without MCP**

- Links: Notion skill docs, Trello skill, RAG pipeline for Notion search.

**Option B:** new route `/integrations/productivity` with three cards (MCP, RAG, Skills).

Pick one; do not build both. Link from `frontend/src/app/(workspace)/settings/page.tsx` MCP card
description or add **Productivity** row pointing to chosen page.

### 5. Example playbook

**`examples/productivity/notion-trello-sync/playbook.yaml`** (NEW)

Demonstrate multi-step workflow (can use stub MCP tool names in comments if tools require live creds):

```yaml
name: notion-trello-weekly-sync
description: Copy open Trello cards from a board into a Notion database summary page.
steps:
  - id: list_cards
    agent: default
    prompt: |
      Using Trello MCP or trello skill, list all open cards on board {board_id}.
  - id: write_notion
    agent: default
    prompt: |
      Using Notion MCP, append a markdown summary of those cards to page {notion_page_id}.
variables:
  board_id: ""
  notion_page_id: ""
```

**`examples/productivity/notion-trello-sync/README.md`**: setup steps (MCP add, OAuth, variables).

### 6. Tests

- Skill loader test: `trello` and `productivity-integrations` appear in `keprix skills list` output
  (follow existing skill list test pattern).
- Playbook YAML parses via playbook loader (if test exists).

---

## Acceptance criteria

1. `keprix skills list` includes `trello` and `productivity-integrations`.
2. Agent with only trello skill (MCP disabled) can list boards when env vars set (manual smoke).
3. `productivity-integrations` skill documents all three paths with correct tool names.
4. Settings or MCP page links to skills/RAG alternatives.
5. Example playbook YAML validates and is linked from README.
6. No em dashes in new markdown (run `python3 scripts/fix-writing-style.py` on new files).

---

## What this prompt does NOT do

- MCP catalog entries (prompt 172).
- OAuth UI (prompt 173).
- Notion RAG connector implementation (prompt 174).
- Full operator guide and evals (prompt 176).
