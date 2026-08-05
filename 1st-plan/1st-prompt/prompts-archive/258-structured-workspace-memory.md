# Keprix - Prompt 258: Structured Workspace Memory and Indexes

**Series:** Agentic OS adoption **256-265**  
**Master reference:** `../prompts-archive/ref-255-agentic-os-adoption-master-reference.md`  
**Supersedes draft:** `245-structured-workspace-memory.md`  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

Level 2 **memory map**: folder templates, auto-generated `index.md` per directory, and `KEPRIX.md` navigation guide (Chase/Karpathy-inspired, optional preset not mandatory).

**Knowledge Pipeline template** (default preset):

```text
workspace/
  raw/          # unstructured inputs
  wiki/         # structured articles
  outputs/      # deliverables
  KEPRIX.md     # navigation guide for the agent
```

Each folder gets `index.md` maintained on file change and on schedule.

**Non-goals:** Force all users into raw/wiki/outputs; blank and domain presets remain available. No Obsidian plugin.

---

## 2. Already built

| Area | Location |
| --- | --- |
| Documents / notes routes | `workspace/routes/` |
| Memory + RAG | `memory/`, `/api/memory/*` |
| llm-wiki skill pattern | `skills/research/llm-wiki/SKILL.md` |
| Project builder | `/projects` scoped memory |
| Context files | `.keprix.md`, `AGENTS.md` injection |

---

## 3. Architecture

```text
File watcher / upload hook
        |
        v
workspace/index_generator.py
        |
        +--> write {folder}/index.md
        |
        v
workspace/keprix_md_generator.py  -->  KEPRIX.md at workspace root
        |
        v
memory_index_bridge.py  --> episodic memory entries for files
```

---

## 4. Template presets

| ID | Folders | Use case |
| --- | --- | --- |
| `knowledge_pipeline` | raw, wiki, outputs | Research -> article -> deliverable |
| `property_investor` | deals, tenants, compliance, reports | Property ops |
| `developer` | specs, architecture, releases, reviews | Software |
| `client_delivery` | clients/, deliverables, feedback | Agency |
| `executive_assistant` | context/, raw, wiki (+ hot.md per **278**), outputs | EA / second brain |
| `blank` | none | Custom |

CLI: `keprix workspace init --template knowledge_pipeline --name my-hub`  
UI: `/workspace/new` template picker.

---

## 5. Index format

Each `index.md` includes: last updated, file table (name, topic, date, status), topic groupings. Generator must be deterministic enough for tests (LLM categorization optional with fallback to filename heuristics).

---

## 6. KEPRIX.md content

- Folder purposes
- Navigation pattern (index first, then target file)
- Reading/writing strategy
- Link to **261** `runs/` logging convention when present
- Link to `context/` folder when present (**276** onboard files)
- Hot cache read order when `wiki/hot.md` exists (**278**)

**Nate Herk extension (**276**, **278**):** `context/` subfolder with `about-business.md`, `about-me.md`, `priorities.md`, `writing-samples.md`, `guardrails.md`, `cadence-preferences.md`. Optional `wiki/hot.md` for `executive_assistant` preset.

Auto-generated on template apply; user-editable; loaded as context file on workspace sessions.

---

## 7. API

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/workspaces` | Create with `template_id` |
| POST | `/api/workspaces/{id}/reindex` | `{ folder?: "wiki" }` |
| GET | `/api/workspaces/templates` | List presets |

---

## 8. Files to create

```
src/keprix/workspace/
  index_generator.py
  template_presets.py
  keprix_md_generator.py
  memory_index_bridge.py
  templates/knowledge_pipeline/...
  templates/property_investor/...
  templates/developer/...
  templates/client_delivery/...
  templates/blank/...

src/keprix/api/workspace_template_routes.py

frontend/src/app/(workspace)/workspace/new/page.tsx

docs/features/structured-workspace-memory.md

tests/workspace/
  test_index_generator.py
  test_template_presets.py
  test_keprix_md_generator.py
  test_memory_index_bridge.py
```

---

## 9. Acceptance criteria

- Template create writes folders + initial `index.md` + `KEPRIX.md`.
- File create/update/delete under watched workspace triggers parent index refresh within 30s (or sync on small workspaces).
- Agent session in workspace loads `KEPRIX.md` via existing context file pipeline.
- `keprix workspace index --folder wiki` works CLI-only.
- Memory search returns workspace file paths linked by bridge.
- Tests do not call live LLM for categorization (mock or heuristic path).

---

## 10. Dependencies

- **Next:** 259 vault uses same folder roots
- **264** starter pack bundles `knowledge_pipeline` template
