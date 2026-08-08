# KNIME Adoption Master Architecture Reference (Keprix 233-238 + Carina knime-adoption)

**Do not archive until the full pack ships.**

**Competitive research:** `planning/competitor-research/knime-visual-workflow-adoption.md`  
**Source mirror (read only):** `planning/competitor-research/agents-to-adopt/knime/`  
**n8n gap register:** `planning/competitor-research/agents-to-adopt/n8n/GAPS-FOR-KEPRIX.md`

---

## 1. Strategic decision (non-negotiable)

| Adopt | Do not port |
| --- | --- |
| Visual node canvas UX | Java Eclipse workbench (`WorkflowEditor.java`) |
| Connector marketplace discoverability | KNIME `knime-base` Java nodes |
| Citizen analyst templates + coach | OSGi plugin SDK |
| Deploy/monitor/drift via Scout | KNIME Server runtime |
| CE free canvas / EE governance split | GPLv3 code in MIT Keprix core |

**One runtime rule:** All authoring paths compile to YAML consumed by `yaml_compiler.compile_playbook_document()` -> `sdk_workflow.start_workflow_run()`.

---

## 2. Authoring modes (after pack ships)

| Mode | Entry | Output |
| --- | --- | --- |
| Hand YAML | Editor, files | YAML |
| Describe tab (208) | StartPlaybookDialog | YAML via LLM |
| Visual Studio (233) | `/playbooks/studio/[id]` | YAML + layout JSON |
| n8n import (238) | CLI or studio import | Canvas -> YAML |
| Template gallery (237) | Studio templates tab | Canvas seed |

---

## 3. Keprix prompt map

| Prompt | Title | Delivers |
| --- | --- | --- |
| **233** | Visual Playbook Studio | React Flow canvas, compile/decompile, persistence, run |
| **234** | Connector catalog marketplace | `/integrations`, 20+ connectors, studio deep links |
| **235** | Community vs Enterprise gates | Edition model; studio never gated |
| **236** | Scout publish + telemetry | Version hash, lifecycle webhooks, run events |
| **237** | Templates, variables, coach | Citizen analyst completeness |
| **238** | Import bridges + run overlay | n8n/YAML import, run visualization on canvas |

Build order: `233-knime-adoption-build-order.md`

---

## 4. Carina prompt map

| Prompt | Title | Delivers |
| --- | --- | --- |
| **00** | Architecture reference | This series map |
| **01** | Agent Studio embed | Carina UI -> Keprix studio |
| **02** | Aiva property starter | Deal analysis template + hire binding |
| **03** | Scout agent lifecycle | Deploy/monitor/drift/retrain dashboard |
| **04** | Integrations hub | Carina marketplace surface |
| **05** | Worker playbook runner | Aiva executes Keprix playbooks |

Build order: `knime-adoption--BUILD-ORDER.md`

---

## 5. System diagram

```text
                    +------------------+
                    |  Carina workspace |
                    |  /agent-studio/   |
                    |  /integrations    |
                    +--------+---------+
                             | handoff JWT / proxy API
                             v
+------------+    +----------------------+    +----------------+
| Operator   |--->| Keprix Visual Studio |--->| yaml_compiler  |
| /playbooks |    | canvas_compiler      |    | sdk_workflow   |
+------------+    +----------+-----------+    +-------+--------+
                             | publish                     |
                             v                             v
                    +--------+---------+          +-------+--------+
                    | Scout lifecycle  |<---------| playbook runs  |
                    | (console)        |  events | /playbooks/id  |
                    +------------------+          +----------------+
                             ^
                             | Aiva worker triggers
                    +--------+---------+
                    | knime-adoption-05|
                    +------------------+
```

---

## 6. Storage layout

```
~/.keprix/playbooks/
├── {id}.yaml                 # runtime document
├── {id}.layout.json          # canvas positions
├── {id}/versions/{hash}.json # publish history (236)
├── templates/                # saved templates (237)
└── org/playbooks/            # enterprise org scope (235)
```

---

## 7. API surface (consolidated)

| Method | Route | Prompt |
| --- | --- | --- |
| GET/PUT | `/api/playbooks/studio/{id}` | 233 |
| POST | `/api/playbooks/studio/compile` | 233 |
| POST | `/api/playbooks/studio/decompile` | 233 |
| POST | `/api/playbooks/studio/{id}/publish` | 236 |
| GET | `/api/playbooks/studio/templates` | 237 |
| POST | `/api/playbooks/studio/import/n8n` | 238 |
| GET | `/api/integrations/catalog` | 234 |
| GET | `/api/licensing/edition` | 235 |
| POST | `/api/playbook-runs/start` | existing |

---

## 8. Scout lifecycle events (236 -> 03)

| Event | Producer | Consumer |
| --- | --- | --- |
| `playbook_publish_requested` | Keprix publish | Scout approve queue |
| `playbook_published` | Keprix / Scout callback | Scout version registry |
| `playbook_run_completed` | Keprix run telemetry | Scout health dashboard |
| `playbook_drift_sample` | Optional agent output hook | Scout drift job |

---

## 9. Terminology (Carina boundary)

| Term | Meaning |
| --- | --- |
| Playbook (Keprix) | Automation workflow graph |
| Playbook (Carina `/playbook`) | Local hardware model discovery |
| Cookbook | Internal only |

See `carina/AGENTS.md`.

---

## 10. Status table (2026-07-09)

| Area | Status | Prompt |
| --- | --- | --- |
| Playbook runtime | Shipped | 51, 207-211 |
| NL to YAML | Shipped | 208 |
| Visual canvas | Shipped | 233 |
| Connector marketplace | Shipped | 234 |
| Edition gates | Shipped | 235 |
| Scout telemetry | Shipped | 236 |
| Variables/coach/templates | Shipped | 237 |
| Import/run overlay | Shipped | 238 |
| Carina embed | Pending | knime-adoption--01 |
| Aiva template | Pending | knime-adoption--02 |
| Scout lifecycle UI | Pending | knime-adoption--03 |
| Carina integrations | Pending | knime-adoption--04 |
| Worker runner | Pending | knime-adoption--05 |

---

## 11. KNIME mirror quick index

| Topic | Path under `agents-to-adopt/knime/` |
| --- | --- |
| Graph runtime | `knime-core/.../workflow/WorkflowManager.java` |
| Node contract | `knime-core/.../node/NodeModel.java` |
| Editor | `knime-workbench/.../editor2/WorkflowEditor.java` |
| Coach | `knime-workbench/.../workflowcoach/` |
| Variables dialog | `knime-workbench/.../WorkflowVariablesDialog.java` |
| Base nodes | `knime-base/` |
| SDK setup | `knime-sdk-setup/README.md` |

Re-clone from Bitbucket; GitHub platform repos return 404. See `knime/README.md`.
