# Keprix Prompt 176: Productivity Integrations - Docs, Evals, and E2E Verification

## Purpose

Ship operator-facing documentation and automated checks so Notion + Trello integrations are
**maintainable and verifiable**. Closes the prompt pack with an agent brief for manual E2E.

Read reference 171. Requires prompts **172-175** complete.

---

## Dependencies

- All productivity integration code from 172-175.
- `docs/integrations/mcp.md`, `docs/features/rag-pipelines.md`, `docs/features/settings.md`.
- Eval harness: `evals/suites/` pattern (see `evals/suites/browser/basics.yaml`).

---

## What to build

### 1. Operator guide

**`docs/integrations/productivity-notion-trello.md`** (NEW)

Sections (write fully):

1. **Overview** - three paths table (MCP, RAG, Skills) with links.
2. **Quick start: Notion live (MCP OAuth)**
   - Browse catalog -> Add Notion -> Connect -> new chat -> example prompts.
3. **Quick start: Notion headless**
   - `notion-token` catalog entry, integration token, page sharing.
4. **Quick start: Trello**
   - API key + token, catalog add, example prompts.
5. **Search Notion with RAG**
   - `KEPRIX_NOTION_TOKEN`, pipeline builder, link from `/admin/mcp`.
6. **Skills fallback**
   - When MCP not configured; `keprix skills config`.
7. **Vault** - storing tokens; link to `/vault`.
8. **Auto-spawn** - explicitly **off** for these servers; link to `/admin/mcp` toggle.
9. **Environment variables** table:

   | Variable | Used by |
   | --- | --- |
   | `KEPRIX_NOTION_TOKEN` | RAG ingest |
   | `NOTION_TOKEN` | notion-token MCP, skill |
   | `TRELLO_API_KEY`, `TRELLO_TOKEN` | Trello MCP, skill |
   | `NEXT_PUBLIC_MCP_API_URL` | Frontend MCP admin API |
   | `KEPRIX_AUTO_MCP_SPAWN` | Agent auto-spawn (not for Notion/Trello) |

10. **Troubleshooting** - OAuth expired, Notion 404 (page not shared), Trello 401, MCP API wrong port.

### 2. Update existing docs

| File | Change |
| --- | --- |
| `docs/integrations/mcp.md` | Link to productivity guide; list Notion/Trello catalog keys |
| `docs/features/rag-pipelines.md` | Replace placeholder Notion section with link to connector + `ingest/notion` API |
| `docs/features/settings.md` | Note productivity integrations under MCP servers card |
| `docs/index.md` | Add row under Integrations if table exists |
| `.env.example` | Ensure `KEPRIX_NOTION_TOKEN` documented (may overlap 174) |
| `frontend/.env.example` | Comment block for MCP API URL (may exist from configurable MCP work) |

### 3. Eval suite

**`evals/suites/productivity/notion-trello.yaml`** (NEW)

Structure:

```yaml
suite: productivity-notion-trello
description: Smoke checks for Notion/Trello integration wiring (mocked backends).
tasks:
  - id: catalog_has_notion_trello
    type: http_get
    path: /api/mcp/catalog
    assert_json:
      catalog_keys_include: [notion, notion-token, trello]

  - id: rag_connectors_list_notion
    type: http_get
    path: /api/rag-pipeline/connectors
    assert_json:
      connector_ids_include: [notion]

  - id: skills_list_productivity
    type: cli
    command: ["keprix", "skills", "list"]
    assert_output_contains: [trello, productivity-integrations]
```

Adapt task types to match the project's eval runner (read `evals/suites/opportunity/basics.yaml`
and implement runnable tasks; if HTTP eval runner does not exist, use pytest-only equivalents in
`src/keprix/tests/evals/test_productivity_integrations.py`).

### 4. Consolidated pytest smoke

**`src/keprix/tests/integrations/test_productivity_notion_trello_pack.py`** (NEW)

Single module that imports and runs:

- Catalog entries present (from 172).
- OAuth status field on server summary (from 173).
- Notion connector registry (from 174).
- Skills registered (from 175).

Mark live-API tests `@pytest.mark.integration` and skip without credentials.

### 5. Agent brief

**`prompts-archive/176-productivity-notion-trello-verification.md`** (NEW)

Manual checklist:

- [ ] Add Notion OAuth from `/admin/mcp`; Connect; verify tools in chat.
- [ ] Add Trello with credentials; "List my boards" works.
- [ ] Ingest one Notion page via RAG builder; query in chat.
- [ ] Disable MCP; verify trello skill lists boards with env vars.
- [ ] Vault-stored TRELLO_TOKEN works on catalog add (if 173 shipped).
- [ ] Docs render in MkDocs / local docs build.

### 6. Audit updates

- Add prompts 172-176 to `planning/prompts/PROMPT-IMPLEMENTATION-AUDIT.md` when each ships.
- Add series table to `planning/prompts/PROMPT-CROSSREF-GUIDE.md`:

```markdown
## Productivity integrations series (171-176)

| Prompt | Role |
| --- | --- |
| 171 | Architecture reference |
| 172 | MCP catalog + optional-mcps manifests |
| 173 | OAuth connect + Vault UX |
| 174 | Notion RAG source connector |
| 175 | Skills + routing + playbook |
| 176 | Docs + evals + verification brief |
```

---

## Acceptance criteria

1. `docs/integrations/productivity-notion-trello.md` exists and builds in docs site.
2. Cross-links from `mcp.md` and `rag-pipelines.md` resolve.
3. Eval suite or pytest smoke passes in CI without live Notion/Trello credentials.
4. Agent brief checklist covers all three integration paths.
5. `PROMPT-CROSSREF-GUIDE.md` includes 171-176 series.
6. Grep for "coming soon" / TODO in 172-175 production modules is clean.

---

## What this prompt does NOT do

- New features beyond documentation, evals, and audit hygiene.
- Video or screenshot assets (optional placeholder SVG ok in `docs/assets/` if needed).
