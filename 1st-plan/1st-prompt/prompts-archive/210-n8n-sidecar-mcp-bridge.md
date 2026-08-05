# Keprix - Prompt 210: n8n Sidecar MCP Bridge (Catalog + Workspace UX)

## Purpose

Close gap **P3** and **N3** from `planning/competitor-research/agents-to-adopt/n8n/GAPS-FOR-KEPRIX.md`.
Do **not** port `nodes-base`. Bridge: run n8n alongside Keprix and manage workflows via MCP.
Manifest exists; ship operator docs, workspace install UX, and migration cross-links.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| n8n MCP manifest | `src/keprix/optional-mcps/n8n/manifest.yaml` |
| MCP catalog CLI | `keprix mcp catalog`, `keprix mcp install` |
| MCP admin API | `GET /api/mcp/catalog` in `mcp_admin_routes.py` |
| Productivity MCP prompts | Archived 172-175 |
| n8n import CLI | Prompt 207 (dependency: cross-link only) |

## Gap

Operators do not know they can use n8n as integration sidecar. No workspace page section for n8n bridge.
Catalog entry may lack docs link and UI discoverability.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Step 1: Manifest polish

Edit `src/keprix/optional-mcps/n8n/manifest.yaml`:

- Add `docs_url: /docs/integrations/n8n-sidecar` (or relative path used by catalog UI)
- Add `category: workflow-bridge`
- Expand `post_install` with Docker one-liner for local n8n:

```text
docker run -d --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

- Clarify read-mostly default tools vs opt-in mutations (already documented; ensure catalog UI shows it)

## Step 2: Operator docs page

Create `docs/integrations/n8n-sidecar.md`:

| Section | Content |
| --- | --- |
| When to use | Customer already runs n8n; needs 300+ connectors without porting nodes |
| Architecture | Keprix agent OS + n8n sidecar via stdio MCP bridge |
| Install | `keprix mcp install n8n`, env vars, API key steps |
| Import path | Link to Prompt 207 `migrate from-n8n` for one-time YAML migration |
| Security | Mutating tools off by default; API key scope |
| Limitations | Fair-code n8n license is customer's; Keprix does not bundle n8n |

Add to docs index / navigation if `docs-catalog` pattern exists (`frontend/src/lib/docs-catalog.ts`).

## Step 3: Workspace integrations UI

Add card to `frontend/src/app/(workspace)/admin/mcp/page.tsx` or `settings/messaging` adjacent integrations hub:

**Card: n8n workflow bridge**

- Status: installed / not installed (from `/api/mcp/catalog`)
- CTA: "Install n8n MCP" opens existing MCP install flow with `n8n` preselected
- Link: docs page
- Secondary: "Import workflow JSON" links to migration doc anchor

If no suitable page exists, add subsection to `frontend/src/app/(workspace)/hub/page.tsx` under Integrations.

## Step 4: Agent routing hint (optional, small)

Add skill or persona routing note in `src/keprix/skills/` or docs only:

When user asks to "run my n8n workflow", agent should prefer n8n MCP tools if installed.

No new agent loop code unless trivial manifest check in tool router docs.

## Step 5: Tests

- `tests/keprix_cli/test_mcp_catalog.py`: assert `n8n` entry loads, has `docs_url`, default tools list
- Smoke: manifest YAML parses via existing catalog loader

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | `keprix mcp catalog` lists `n8n` with updated description |
| 2 | `docs/integrations/n8n-sidecar.md` exists and is linked from docs catalog |
| 3 | Workspace UI shows n8n bridge card with install CTA |
| 4 | Migration doc cross-links n8n sidecar vs import CLI |
| 5 | `pytest tests/keprix_cli/test_mcp_catalog.py` passes (extend if needed) |

## Dependencies

- Prompt 207 recommended first (import CLI cross-link); can ship in parallel.

## Archive

`prompts-archive/` when AC pass.
