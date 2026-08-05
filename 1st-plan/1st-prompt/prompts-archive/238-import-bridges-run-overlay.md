# Keprix - Prompt 238: Import Bridges and Run-State Canvas Overlay

**Series:** KNIME adoption pack **233-238** (final Keprix prompt in pack)  
**Principle:** **Bridge** existing formats (n8n JSON, YAML files) into the studio canvas; **visualize runs** on the graph like KNIME's executed node states, without porting n8n editor code.

**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

| Feature | Description |
| --- | --- |
| n8n -> canvas import | Convert n8n workflow JSON to studio canvas (extends 207) |
| YAML file import | Upload `.yaml` playbook into studio |
| Run overlay | View completed/in-progress run with node status colors on canvas |
| Export bundle | Download `{id}.yaml` + `{id}.layout.json` zip |

---

## 2. Reference implementations (read only)

| Source | Path | Use |
| --- | --- | --- |
| n8n converter | `src/keprix/backend/migration/n8n_converter.py` | Node type mapping |
| n8n editor | `agents-to-adopt/n8n/packages/frontend/editor-ui/` | Position heuristics only |
| KNIME node states | `knime-core/.../NodeContainerState.java` | Status enum inspiration |
| Run timeline | `PlaybookStepTimeline.tsx` | Event -> node status map |

---

## 3. Already built

| Area | Location |
| --- | --- |
| n8n -> YAML CLI | `keprix migrate from-n8n`, `n8n_converter.py` |
| Studio compile/decompile | Prompt **233** |
| Run events API | `playbook-api.ts`, run detail page |
| Template catalog | Prompt **237** |

---

## 4. n8n JSON to canvas

Create `src/keprix/playbook/n8n_canvas_importer.py`:

```python
def n8n_workflow_to_canvas(payload: dict) -> dict:
    """n8n workflow JSON -> canvas document."""

def n8n_to_canvas_warnings(payload: dict) -> list[str]:
    """Unmapped node types, unsupported connections."""
```

### 4.1 Mapping table (v1)

| n8n node type | Canvas type | Notes |
| --- | --- | --- |
| `n8n-nodes-base.manualTrigger` | trigger | |
| `n8n-nodes-base.scheduleTrigger` | trigger | cron in description |
| `@n8n/n8n-nodes-langchain.agent` | agent_task | map tools if present |
| `n8n-nodes-base.httpRequest` | http | url, method |
| `n8n-nodes-base.if` | condition | expression from conditions |
| `n8n-nodes-base.switch` | condition | first rule only + warning |
| `n8n-nodes-base.slack` etc. | agent_task or http | warning + stub |
| Unmapped | skip | collect warning |

Reuse position from n8n `position: [x,y]` when present; else auto-layout.

### 4.2 API

```
POST /api/playbooks/studio/import/n8n
Body: { workflow: object } OR multipart file
Response: { canvas, warnings, suggested_id }
```

Studio toolbar **Import n8n** -> file picker -> preview warnings -> **Open in studio**.

CLI convenience (optional):

```bash
keprix playbooks import-n8n workflow.json --open-studio
```

---

## 5. YAML file import

```
POST /api/playbooks/studio/import/yaml
Body: { yaml: string, playbook_id?: string }
Response: { canvas, playbook_id }
```

Studio toolbar **Import YAML** -> paste or upload -> decompile via 233 API.

Validate with `compile_playbook_document` before save.

---

## 6. Run-state canvas overlay

### 6.1 Node status model

Create `frontend/src/lib/playbook-studio/runOverlay.ts`:

```typescript
type NodeRunStatus = "pending" | "running" | "completed" | "failed" | "skipped" | "waiting_approval";

function mapEventsToNodeStatus(
  events: PlaybookRunEvent[],
  nodeIds: string[],
): Record<string, NodeRunStatus>;
```

Map from existing event types:

| Event | Node status |
| --- | --- |
| `playbook.node.started` | running |
| `playbook.node.completed` | completed |
| `playbook.node.failed` | failed |
| `playbook.node.approval.requested` | waiting_approval |
| no events | pending |

### 6.2 UI entry points

| Entry | Behavior |
| --- | --- |
| Run detail page | Button **View on canvas** -> `/playbooks/studio/{playbookId}?run={runId}` |
| Studio with `?run=` | Read-only canvas; nodes colored by status; inspector shows step output snippet |
| Live run | Poll run events every 2s until terminal; animate running node |

Read-only mode: disable palette drops and save; toolbar shows **Back to run timeline**.

### 6.3 Visual styling

| Status | Node border/background |
| --- | --- |
| pending | default |
| running | pulsing primary border |
| completed | green border |
| failed | red border |
| waiting_approval | amber border |
| skipped | dashed gray |

Match `PlaybookStepTimeline` chip colors for consistency.

---

## 7. Export bundle

```
GET /api/playbooks/studio/{id}/export
Response: application/zip with {id}.yaml + {id}.layout.json + README.txt
```

README.txt explains import on another Keprix instance (no KNIME `.knwf` format).

---

## 8. Tests

`tests/playbook/test_n8n_canvas_importer.py`:

- Fixture: minimal n8n workflow JSON from `tests/fixtures/n8n/`
- Assert canvas node count + compile success
- Assert warnings for unmapped nodes

`tests/playbook/test_import_yaml.py`  
Frontend unit: `runOverlay.test.ts` event mapping

---

## 9. Documentation

Add `docs/features/playbook-import-export.md`:

- n8n import limits (bridge not parity)
- YAML import/export
- Run overlay operator guide
- Explicit: does not export to KNIME format

Update `docs/integrations/n8n-sidecar.md` cross-link.

---

## 10. Acceptance criteria

| # | Test |
| --- | --- |
| 1 | n8n fixture imports to canvas with >= 2 nodes |
| 2 | Imported canvas compiles via yaml_compiler |
| 3 | Warnings shown for unmapped n8n nodes |
| 4 | YAML upload opens in studio with layout |
| 5 | Run overlay colors nodes from timeline events |
| 6 | Read-only overlay does not allow save |
| 7 | Export zip contains yaml + layout |
| 8 | pytest passes |
| 9 | No n8n Vue code copied |

---

## 11. Out of scope

| Item | Notes |
| --- | --- |
| n8n bidirectional export | Import only |
| KNIME .knwf import | Unsupported |
| Real-time websocket run updates | Polling ok v1 |
| Edit canvas during run | Read-only overlay |

---

## 12. Archive

`prompts-archive/238-import-bridges-run-overlay.md` when AC pass. Update master build order to mark KNIME Keprix pack complete.
