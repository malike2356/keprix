# Keprix - Prompt 233: Visual Playbook Studio (KNIME-Style Canvas)

**Series:** KNIME adoption pack **233-238** (233 studio, 234 connectors, 235 editions, 236 Scout bridge, 237 templates/variables/coach, 238 import/run overlay). ML service remains **229-232** (separate).

**Platform:** Keprix agent OS  
**Principle:** Adopt KNIME **UX patterns**, not KNIME **Java runtime**. One durable playbook engine (`yaml_compiler` + `sdk_workflow`); canvas is a compile target, not a second product.

**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

A **Visual Playbook Studio**: drag-and-drop node canvas that compiles to existing Keprix YAML and runs through the shipped durable runtime. Operators get KNIME/n8n-style authoring without forking Eclipse, OSGi, or GPLv3 code.

| Surface | Route | Role |
| --- | --- | --- |
| Studio editor | `/playbooks/studio/[id]` | React Flow canvas + inspector |
| Studio API | `/api/playbooks/studio/*` | Save, compile, decompile, list |
| Run (unchanged) | `POST /api/playbook-runs/start` | Existing durable execution |
| Run UI (unchanged) | `/playbooks/[runId]` | `PlaybookStepTimeline` |

**Non-goals (hard):**

- Do not port `WorkflowEditor.java`, `NodeModel.java`, or any KNIME workbench code into Keprix.
- Do not add a second workflow engine or n8n `nodes-base` port.
- Do not ship parallel/artifact/browser_action on canvas in v0 (runtime supports them; canvas v1 in prompt 237).

---

## 2. KNIME mirror study map (read only)

Use the Bitbucket mirror at `planning/competitor-research/agents-to-adopt/knime/` to answer UX questions. **Study patterns; rewrite in TypeScript/Python.**

| KNIME concept | Mirror path | Keprix equivalent |
| --- | --- | --- |
| Graph runtime | `knime-core/.../workflow/WorkflowManager.java` | `sdk_workflow.py`, `runtime/runner.py` |
| Node vertex | `knime-core/.../workflow/NodeContainer.java` | Canvas `nodes[]` entry + YAML step |
| Node execution contract | `knime-core/.../node/NodeModel.java` | `_map_yaml_step()` in `yaml_compiler.py` |
| Visual editor shell | `knime-workbench/.../editor2/WorkflowEditor.java` | `PlaybookCanvas.tsx` |
| Drop node onto canvas | `WorkflowEditorDropTargetListener.java` | React Flow `onDrop` from palette |
| Node config dialog | `WrappedNodeDialog.java` | `NodeInspector.tsx` |
| Auto layout | `org.knime.workbench.ui.layout/` | `autoLayout.ts` (dagre, v0) |
| Next-node suggestions | `workflowcoach/WorkflowCoachView.java` | Prompt **237** coach panel |
| Workflow variables | `WorkflowVariablesDialog.java` | Prompt **237** variables panel |

Also read n8n mirror for Vue canvas patterns: `agents-to-adopt/n8n/packages/frontend/editor-ui/` (study only).

---

## 3. Already built (do not reimplement)

| Area | Location |
| --- | --- |
| YAML compile to graph | `src/keprix/playbook/yaml_compiler.py` (`compile_playbook_document`, lines 12-43) |
| Step type mapping | `yaml_compiler._map_yaml_step` (lines 46-101) |
| Edge normalization | `yaml_compiler._normalize_edges` (lines 104-154) |
| Durable runtime | `src/keprix/playbook/sdk_workflow.py` (`compile_workflow_spec`, `start_workflow_run`) |
| Start run API | `src/keprix/playbook/run_routes.py` (`POST /api/playbook-runs/start`) |
| Graph templates | `src/keprix/playbook/graph_catalog.py` |
| Run step timeline UI | `frontend/src/components/playbooks/PlaybookStepTimeline.tsx` |
| Playbooks list | `frontend/src/app/(workspace)/playbooks/page.tsx` |
| Start dialog | `frontend/src/components/playbooks/StartPlaybookDialog.tsx` |
| NL to YAML | `src/keprix/playbook/nl_builder.py` (prompt 208) |
| Condition sandbox | `src/keprix/playbook/expression_sandbox.py` (prompt 211) |
| n8n YAML import | `src/keprix/backend/migration/n8n_converter.py` (prompt 207) |
| Agent Studio chip canvas | `frontend/src/components/agent-studio/AgentCanvas.tsx` (different product; do not reuse for playbooks) |

---

## 4. Architecture

```text
/playbooks/studio/[id]  (Next.js + @xyflow/react)
        |
        |  canvas JSON { nodes, edges, variables?, layout meta }
        v
canvas_compiler.py  -->  playbook YAML document { id, name, steps[], edges[], entry }
        |
        v
yaml_compiler.compile_playbook_document()   [EXISTING]
        |
        v
sdk_workflow.compile_workflow_spec() / start_workflow_run()   [EXISTING]
        |
        v
POST /api/playbook-runs/start  -->  PlaybookStepTimeline
```

**Roundtrip:** YAML on disk <-> canvas via `canvas_decompiler.py`. Layout positions stored separately in `{id}.layout.json` so YAML stays runtime-clean.

---

## 5. Canvas document schema

### 5.1 Top-level shape

```json
{
  "schema_version": 1,
  "id": "daily-digest",
  "name": "Daily digest",
  "description": "Optional operator description",
  "entry": "fetch_emails",
  "nodes": [],
  "edges": [],
  "viewport": { "x": 0, "y": 0, "zoom": 1 }
}
```

Storage split:

| File | Contents |
| --- | --- |
| `~/.keprix/playbooks/{id}.yaml` | Runtime playbook document (no x/y positions) |
| `~/.keprix/playbooks/{id}.layout.json` | Node positions, viewport, optional groups |

### 5.2 Node shape (React Flow compatible)

```json
{
  "id": "fetch_emails",
  "type": "agent_task",
  "position": { "x": 120, "y": 80 },
  "data": {
    "label": "Fetch emails",
    "prompt": "Summarize unread inbox threads",
    "tools": [],
    "connector_id": null
  }
}
```

### 5.3 Edge shape

```json
{
  "id": "e_fetch_to_summarize",
  "source": "fetch_emails",
  "target": "summarize",
  "sourceHandle": null,
  "targetHandle": null,
  "data": { "when": null }
}
```

For condition nodes, two outgoing edges use `data.when`: `"true"` or `"false"` (matches `yaml_compiler._normalize_edges`).

### 5.4 Canvas node types (v0)

| Canvas `type` | Palette label | YAML `type` | Runtime `type` |
| --- | --- | --- | --- |
| `trigger` | Trigger | (sets `entry` only) | entry metadata |
| `agent_task` | LLM / Agent | `agent_task` | `agent_task` |
| `http` | HTTP | `http` | `http` |
| `condition` | Condition | `condition` | `condition` |
| `human_approval` | Approval | `human_approval` | `approval` |

**Trigger node rule:** Exactly one trigger per graph in v0. Its `id` becomes `entry`. Trigger has no incoming edges; one outgoing edge minimum before run.

---

## 6. Backend: canvas compiler

Create `src/keprix/playbook/canvas_compiler.py`:

```python
def compile_canvas_document(canvas: dict) -> dict:
    """Canvas JSON -> playbook YAML document ready for yaml_compiler."""

def validate_canvas_document(canvas: dict) -> list[str]:
    """Return human-readable errors/warnings (empty if valid)."""

def canvas_to_yaml_steps(canvas: dict) -> tuple[list[dict], list[dict], str | None]:
    """Return (steps, edges, entry_id)."""
```

### 6.1 Compilation rules

1. **Trigger:** Find single node with `type == "trigger"`. Set `entry` to its id. Do not emit a YAML step for trigger (metadata only). If no trigger, use first node with no incoming edges; if ambiguous, error.
2. **Steps:** For each non-trigger node, map `data` fields to YAML step fields per table in section 5.4.
3. **Condition:** Require `expression` in `data`. Outgoing edges must include `when: true` and `when: false` targets (or set `on_true`/`on_false` on YAML step from edge targets).
4. **agent_task tools:** `data.tools` is string list; validate tool names against registry when `KEPRIX_STUDIO_STRICT_TOOLS=1` (default off in dev).
5. **http:** Require non-empty `url`; default `method` GET.
6. **human_approval:** Map `message`, `risk` (low|medium|high), `summary`.
7. **Ids:** Must match `^[a-z][a-z0-9_]{0,63}$`; reject duplicates.
8. **Graph validity:** No cycles except through condition rejoin (DAG with condition branches). Orphan nodes (no path from entry) -> warning, not hard error in v0.

### 6.2 Validation errors (422 examples)

| Code | Message |
| --- | --- |
| `missing_entry` | No trigger or entry node found |
| `duplicate_node_id` | Duplicate step id `{id}` |
| `condition_missing_branches` | Condition `{id}` needs true and false outgoing edges |
| `invalid_step_id` | Step id `{id}` must be snake_case |
| `empty_agent_prompt` | Agent task `{id}` requires a prompt |
| `http_missing_url` | HTTP step `{id}` requires url |

After compile, always pipe through `compile_playbook_document()` in tests to catch runtime mapping errors.

---

## 7. Backend: canvas decompiler

Create `src/keprix/playbook/canvas_decompiler.py`:

```python
def decompile_playbook_document(parsed: dict, *, layout: dict | None = None) -> dict:
    """YAML document -> canvas JSON."""

def auto_layout_nodes(steps: list[dict], edges: list[dict]) -> dict[str, dict]:
    """Return { step_id: {x, y} } using simple layered DAG layout."""
```

### 7.1 Decompile rules

1. Insert synthetic **trigger** node pointing at `parsed["entry"]` if present.
2. Map YAML types back to canvas types (`approval` -> `human_approval`).
3. Merge positions from `layout.json` when present; else `auto_layout_nodes`.
4. Preserve condition `on_true`/`on_false` as edge `when` values.
5. Never lose step ids on roundtrip (AC requirement).

Port auto-layout logic to frontend `frontend/src/lib/playbook-studio/autoLayout.ts` for client-side preview; backend copy for decompile API consistency.

---

## 8. Backend: persistence and routes

Create `src/keprix/playbook/studio_store.py`:

```python
class PlaybookStudioStore:
    def list_playbooks(self) -> list[dict]: ...
    def load(self, playbook_id: str) -> tuple[dict, dict | None]: ...  # yaml + layout
    def save(self, playbook_id: str, yaml_doc: dict, layout: dict | None) -> None: ...
    def delete(self, playbook_id: str) -> None: ...
```

Directory: `~/.keprix/playbooks/` (create on first save). Use same path convention as docs promise for custom playbooks.

Create `src/keprix/playbook/studio_routes.py`:

| Method | Route | Body | Response |
| --- | --- | --- | --- |
| GET | `/api/playbooks/studio` | - | `{ playbooks: [{ id, name, updated_at }] }` |
| GET | `/api/playbooks/studio/{id}` | - | `{ yaml, layout, canvas }` |
| PUT | `/api/playbooks/studio/{id}` | `{ canvas }` or `{ yaml }` | `{ saved: true, compile_errors: [] }` |
| DELETE | `/api/playbooks/studio/{id}` | - | `{ deleted: true }` |
| POST | `/api/playbooks/studio/compile` | `{ canvas }` | `{ yaml, errors: [] }` or 422 |
| POST | `/api/playbooks/studio/decompile` | `{ yaml: string }` | `{ canvas }` |
| POST | `/api/playbooks/studio/{id}/publish` | `{ note?: string }` | `{ version_hash, status }` (stub for 236) |

Register router in `src/keprix/api/server.py` alongside `run_routes`. Session auth same as playbook runs.

**Publish (v0 stub):** Compute SHA256 of canonical YAML; return `version_hash`. Emit audit log line locally. Full Scout webhook in prompt **236**.

---

## 9. Frontend: dependencies and file tree

Add to `frontend/package.json`:

```json
"@xyflow/react": "^12.3.0",
"dagre": "^0.8.5",
"@types/dagre": "^0.7.52"
```

Create:

```
frontend/src/
├── app/(workspace)/playbooks/studio/
│   ├── page.tsx                    # redirect /studio -> /studio/new
│   └── [id]/page.tsx               # main editor
├── components/playbooks/studio/
│   ├── PlaybookStudioShell.tsx     # toolbar + 3-column layout
│   ├── PlaybookCanvas.tsx          # React Flow wrapper
│   ├── NodePalette.tsx             # draggable node types
│   ├── NodeInspector.tsx           # selected node form
│   ├── StudioToolbar.tsx           # Save, Run, Export YAML, Publish
│   ├── CompileErrorPanel.tsx       # 422 errors inline
│   ├── nodes/
│   │   ├── TriggerNode.tsx
│   │   ├── AgentTaskNode.tsx
│   │   ├── HttpNode.tsx
│   │   ├── ConditionNode.tsx
│   │   └── HumanApprovalNode.tsx
│   └── hooks/
│       ├── usePlaybookStudio.ts    # load/save/compile state
│       └── useStudioRun.ts         # Run -> start API
└── lib/playbook-studio/
    ├── playbook-studio-api.ts
    ├── canvas-types.ts
    ├── node-registry.ts
    └── autoLayout.ts
```

### 9.1 UX requirements (KNIME-inspired)

**Layout (3 columns):**

| Column | Width | Content |
| --- | --- | --- |
| Left | 240px | Node palette + template shortcuts (237) |
| Center | flex | React Flow canvas with snap grid (20px), minimap, zoom controls |
| Right | 320px | Node inspector OR compile errors |

**Toolbar actions:**

| Action | Behavior |
| --- | --- |
| Save | PUT canvas; persist layout + compiled YAML |
| Run | Compile; on success POST `/api/playbook-runs/start`; navigate `/playbooks/{runId}` |
| Export YAML | Download `{id}.yaml` |
| Open Advanced | Open StartPlaybookDialog with YAML prefilled (optional) |
| Auto layout | Re-run dagre on all nodes |
| Validate | POST compile; show errors in panel |

**Palette drag:** `onDragStart` sets `application/reactflow` payload with node type; canvas `onDrop` creates node at pointer with unique id (`{type}_{n}`).

**Condition node handles:** Two source handles (true/false) on right side; edges tagged in `data.when`.

**Empty state:** `/playbooks/studio/new` creates unsaved canvas with trigger + one agent_task stub.

### 9.2 Node inspector fields

| Node type | Fields |
| --- | --- |
| trigger | Label, description (optional cron note as read-only help text) |
| agent_task | Label, prompt (textarea), tools (multi-select from tool registry API) |
| http | Label, url, method, headers (key-value), body (JSON textarea) |
| condition | Label, expression (with link to expression sandbox docs), branch labels |
| human_approval | Label, message, risk select, summary |

Use `{{ steps.<id>.output }}` helper chips in prompt/body fields (KNIME variable picker lite; full panel in 237).

### 9.3 Navigation updates

In `frontend/src/lib/navigation.ts`, under Automations:

- `/playbooks` label unchanged
- Add secondary action on playbooks page: **New in Studio** -> `/playbooks/studio/new`

Update `StartPlaybookDialog.tsx`:

- After Describe tab generates YAML, show **Open in Studio** button -> POST decompile -> navigate `/playbooks/studio/{id}` with imported canvas.

---

## 10. Node visual design

Match existing Keprix MUI workspace chrome. Node colors (consistent with `PlaybookStepTimeline` status chips):

| Type | Header color | Icon (lucide) |
| --- | --- | --- |
| trigger | neutral | Play |
| agent_task | primary | Bot |
| http | info | Globe |
| condition | warning | GitBranch |
| human_approval | secondary | UserCheck |

Selected node: 2px outline. Invalid node (compile error referencing id): red border.

---

## 11. Integration points (follow-on prompts)

| Hook | Prompt | Notes |
| --- | --- | --- |
| Connector sample node prefill | **234** | `?connector={id}` query on `/playbooks/studio/new` |
| Scout publish webhook | **236** | `POST .../publish` emits `playbook_publish_requested` |
| Template gallery + variables | **237** | Left panel tabs |
| n8n JSON import | **238** | Toolbar **Import n8n** |
| Run overlay on canvas | **238** | View run on canvas from run detail page |
| Carina embed | `knime-adoption--01` | Same routes, handoff token |
| Edition gates | **235** | Studio never gated |

---

## 12. Tests

Create `tests/playbook/test_canvas_compiler.py`:

| Test | Assert |
| --- | --- |
| `test_compile_simple_linear` | trigger -> agent -> http compiles; `compile_playbook_document` succeeds |
| `test_compile_condition_branches` | true/false edges; condition expression preserved |
| `test_compile_rejects_cycle` | validation error or runtime graph error |
| `test_compile_rejects_duplicate_ids` | 422 |
| `test_decompile_roundtrip` | save fixture YAML -> canvas -> YAML equals step ids and edges |
| `test_trigger_sets_entry` | entry matches trigger id |
| `test_layout_persisted_separately` | positions in layout file not in YAML |

Fixtures in `tests/fixtures/playbooks/canvas/`:

- `linear_three_node.json`
- `condition_branch.json`
- `invalid_missing_entry.json`

Create `tests/playbook/test_studio_routes.py` (FastAPI TestClient):

- List empty store
- PUT save + GET load roundtrip
- Compile 422 on invalid canvas

Frontend: optional Playwright smoke in `frontend/e2e/playbook-studio.spec.ts` (save + run button enabled).

---

## 13. Documentation

Update `docs/features/playbooks.md`:

- Section **Visual Playbook Studio**
- Authoring modes table: YAML hand-edit, Describe tab (208), Studio canvas (233)
- Storage paths `~/.keprix/playbooks/`
- Operator copy: **playbook** only (never workflow, recipe, KNIME workflow)

Update `planning/competitor-research/knime-visual-workflow-adoption.md` status row for canvas editor.

---

## 14. Acceptance criteria

| # | Test |
| --- | --- |
| 1 | `compile_canvas_document` + `compile_playbook_document` succeeds for 3-node linear fixture |
| 2 | Condition graph with true/false branches compiles and runs in mock runtime |
| 3 | `decompile_playbook_document` roundtrips step ids without loss |
| 4 | `PUT /api/playbooks/studio/{id}` persists YAML + layout under `~/.keprix/playbooks/` |
| 5 | Studio UI: add all five node types, connect edges, save, reload preserves layout |
| 6 | **Run** starts via `POST /api/playbook-runs/start`; run page shows timeline events |
| 7 | Invalid graph returns 422 with `compile_errors` array |
| 8 | `pytest tests/playbook/test_canvas_compiler.py tests/playbook/test_studio_routes.py` pass |
| 9 | No new workflow runtime module; all runs use `start_workflow_run` |
| 10 | `StartPlaybookDialog` **Open in Studio** works for Describe-generated YAML |
| 11 | `/playbooks` shows **New in Studio** entry point |
| 12 | No GPLv3 Java code copied into repo; no `@xyflow` fork |
| 13 | Architecture reference status table updated to **Shipped** for canvas editor |
| 14 | Operator strings say playbook; generated YAML uses existing expression syntax (211) |

---

## 15. Out of scope (explicit deferrals)

| Item | Prompt |
| --- | --- |
| Connector catalog UI | **234** |
| Scout webhook delivery | **236** |
| Template gallery, variables panel, workflow coach | **237** |
| n8n canvas import, run-state overlay | **238** |
| Real-time CRDT multi-user editing | Future |
| Carina iframe embed | `knime-adoption--01` |
| parallel, artifact, browser_action canvas nodes | **237** v1 |

---

## 16. Archive

When all AC pass:

1. Move to `planning/prompts/prompts-archive/233-visual-playbook-studio.md`
2. Update `planning/PROMPT-IMPLEMENTATION-AUDIT.md`
3. Update `prompts-archive/ref-233-visual-playbook-studio-architecture-reference.md` status table
