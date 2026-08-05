# Keprix - Prompt 228: Built Apps Navigation Docs and Verification

## Context

Finish the **223-228** series: operator docs, docs index link, file guards, writing-style scan, archive prompts **224-227**.

Depends on **224-227**.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Step 1: Operator doc

Create `docs/features/built-apps-navigation.md`:

| Section | Content |
| --- | --- |
| Overview | Two-layer nav (platform sidebar + app content shell) |
| For operators | How installed apps appear; one entry per app |
| For app builders | `built_app.yaml`, route convention, `BuiltAppLayout` kit |
| Inner nav patterns | sections vs sub_rail vs tabs |
| Agent Apps vs built apps | When to use `/agent-apps` vs `/apps/[slug]` |
| AbbiS note | Product UI lives in `apps-on-keprix/`; uses Keprix shell primitives |
| Troubleshooting | App missing from sidebar, manifest validation errors |

## Step 2: Cross-links

Update:

- `docs/features/workspace.md` (navigation section)
- `docs/index.md` (Features table: Built apps navigation)
- `prompts-archive/ref-223-built-apps-navigation-architecture-reference.md` status line if needed

## Step 3: Pytest guards

`tests/frontend/test_built_apps_navigation.py` (complete):

- Sidebar collapse files exist (**224**)
- `components/built-app/` kit exists (**225**)
- `built_apps` API module exists (**226**)
- `/apps/[slug]/layout.tsx` exists (**227**)
- `examples/built-app-starter/built_app.yaml` exists

## Step 4: Writing style

From repo root (if script exists):

```bash
python3 scripts/fix-writing-style.py --check docs/features/built-apps-navigation.md
```

Otherwise manual scan: no em dashes, no emojis.

## Step 5: Archive

Move to `planning/prompts/prompts-archive/`:

- `224-workspace-sidebar-collapsible-groups.md`
- `225-built-app-layout-primitives.md`
- `226-built-apps-registry-and-launcher-nav.md`
- `227-built-app-route-host-and-sample-shell.md`
- `228-built-apps-navigation-docs-and-verification.md`

Update:

- `pending-prompts/README.md`
- `PROMPT-CROSSREF-GUIDE.md` (new series table)
- `PROMPT-IMPLEMENTATION-AUDIT.md`

## Step 6: Consumer handoff (documentation only)

Add short section to `examples/built-app-starter/README.md`:

- How eng ABBIS should mount under `/apps/abbis`
- Link to AbbiS planning in `verlox/apps-on-keprix/abbis/` (path reference only)

No AbbiS code in this prompt.

## Acceptance criteria

- Docs complete and linked from docs index
- Pytest guard file passes
- Prompts 224-228 archived
- Audit and crossref updated
- Manual QA checklist documented in operator doc:

| Check | Pass |
| --- | --- |
| Collapsible platform groups | |
| Starter app in Installed apps | |
| Inner section nav on `/apps/starter` | |
| Chat reachable without leaving Keprix shell | |

## Out of scope

- Playwright E2E (optional follow-up)
- Built app marketplace install UX
- Collapsed icon rail for platform sidebar
