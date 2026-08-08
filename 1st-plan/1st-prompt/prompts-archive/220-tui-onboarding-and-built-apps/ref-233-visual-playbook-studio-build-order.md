# Visual Playbook Studio build order (prompt 233)

Architecture reference: `233-visual-playbook-studio-architecture-reference.md`  
Series build order: `233-knime-adoption-build-order.md`

---

## Phase 1: Compile layer (backend, no UI)

1. `playbook/canvas_compiler.py` (canvas JSON -> YAML document)
2. `playbook/canvas_decompiler.py` (YAML -> canvas JSON)
3. `playbook/studio_store.py` (read/write `~/.keprix/playbooks/`)
4. `playbook/studio_routes.py` (CRUD + compile/decompile)
5. `tests/playbook/test_canvas_compiler.py`

**Gate:** Roundtrip tests pass; `compile_playbook_document` accepts studio output.

---

## Phase 2: Studio UI (frontend)

1. React Flow canvas with five node types
2. `/playbooks/studio/[id]` page (palette, canvas, inspector panel)
3. Save/load via studio API
4. **Run** button -> `POST /api/playbook-runs/start` with compiled steps/edges
5. Link from `/playbooks` and StartPlaybookDialog

**Gate:** Manual E2E: draw 3-node graph, run, see `PlaybookStepTimeline` events.

---

## Phase 3: Polish and docs

1. `docs/features/playbooks.md` section **Visual Studio**
2. Property starter template optional (`examples/playbooks/aiva-deal-analyse.yaml`)
3. Update architecture reference status table
4. Archive prompt 229

---

## Dependencies

| Dependency | Required for |
| --- | --- |
| Prompt 208 (NL YAML) | Optional; Open in Studio from Describe tab |
| Prompt 207 (n8n) | Optional; future import to canvas |
| Prompt 211 (expressions) | Condition node expression validation |

229 can ship without Carina UI changes.
