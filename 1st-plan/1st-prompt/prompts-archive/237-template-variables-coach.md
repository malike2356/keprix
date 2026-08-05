# Keprix - Prompt 237: Template Catalog, Workflow Variables, and Coach Panel

**Series:** KNIME adoption pack **233-238**  
**Principle:** KNIME **Workflow Coach** and **Workflow Variables** help citizen analysts; rebuild as Keprix-native studio panels, not Java imports.

**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

Three studio enhancements that complete the KNIME-style **citizen analyst** experience:

| Feature | KNIME analog | Keprix deliverable |
| --- | --- | --- |
| Template catalog | Workflow templates / examples | Gallery from `graph_catalog` + custom saved |
| Workflow variables | `WorkflowVariablesDialog.java` | Playbook variables panel + `{{ state.* }}` |
| Coach panel | `WorkflowCoachView.java` | Next-node suggestions based on selection |

Depends on prompt **233** studio shell.

---

## 2. KNIME mirror study map

| File | Study for |
| --- | --- |
| `knime-workbench/.../WorkflowVariablesDialog.java` | Variable types, scope, UI grouping |
| `knime-workbench/.../workflowcoach/WorkflowCoachView.java` | Successor node recommendations |
| `knime-examples/` | Example graph patterns |
| `graph_catalog.py` | Existing Keprix templates |

---

## 3. Already built

| Area | Location |
| --- | --- |
| Graph templates API | `graph_catalog.py`, `GET /api/playbook-runs/graphs` |
| Expression refs | `expression_sandbox.py` (`{{ steps.id.output }}`, `{{ state.key }}`) |
| NL to YAML | `nl_builder.py` |
| Studio shell | Prompt **233** |
| Aiva template YAML | Prompt **02** / `knime-adoption--02` |

---

## 4. Workflow variables

### 4.1 Schema extension

Add optional top-level `variables` to playbook YAML and canvas JSON:

```yaml
id: deal-flow
variables:
  - name: client_email
    type: string
    default: ""
    description: Recipient for final report
  - name: min_score
    type: number
    default: 65
```

Canvas mirror in `canvas.variables[]` with same shape.

Types v1: `string`, `number`, `boolean` (no file/blob).

### 4.2 Runtime injection

Create `src/keprix/playbook/variable_context.py`:

```python
def build_initial_state(variables: list[dict], overrides: dict | None) -> dict:
    """Merge defaults + run overrides into state.* namespace."""

def validate_variable_refs(yaml_doc: dict) -> list[str]:
    """Find {{ state.X }} refs where X not declared; warnings only in v1."""
```

Wire into `start_workflow_run` initial_state when run started from studio with variable form.

### 4.3 Studio UI: Variables panel

Add tab **Variables** in left column (below palette):

| Column | Field |
| --- | --- |
| Name | snake_case input |
| Type | select |
| Default | typed input |
| Description | optional |

Toolbar **Run** opens dialog when variables exist: edit values before start.

Inspector helper: insert `{{ state.var_name }}` chip into focused field.

---

## 5. Template catalog

### 5.1 Catalog sources

Create `src/keprix/playbook/template_catalog.py`:

```python
def list_templates(*, include_custom: bool = True) -> list[dict]:
    """Merge PLAYBOOK_GRAPH_CATALOG + ~/.keprix/playbooks/templates/ + featured seeds."""

def get_template(template_id: str) -> dict | None: ...

def save_as_template(playbook_id: str, *, title, description) -> str:
    """Copy saved playbook to templates dir; return template_id."""
```

Featured seeds (decompile to canvas on open):

| template_id | Title | Source |
| --- | --- | --- |
| `sdk-workflow` | SDK workflow | graph_catalog |
| `research-deep-dive` | Research deep dive | graph_catalog |
| `aiva-deal-analyse` | Aiva deal analysis | knime-adoption--02 |
| `daily-digest` | Daily digest | new YAML example |
| `support-triage` | Support triage | new: trigger -> agent -> condition -> approval |

### 5.2 Studio UI: Templates tab

Left panel tab **Templates**:

- Searchable list with title + description
- **Use template** -> replaces canvas (confirm if unsaved changes)
- **Save as template** (from toolbar) -> dialog title/description

API:

```
GET /api/playbooks/studio/templates
POST /api/playbooks/studio/templates/from/{playbook_id}
```

---

## 6. Workflow coach panel

KNIME Workflow Coach suggests successor nodes. Keprix v1 uses **static rules**, not ML.

Create `src/keprix/playbook/workflow_coach.py`:

```python
COACH_RULES: list[CoachRule] = [
    # after trigger -> suggest agent_task
    # after agent_task -> suggest condition, http, human_approval
    # after condition -> suggest agent_task on each branch
    # after human_approval -> suggest agent_task (send/output)
]

def suggest_next_nodes(
    *,
    selected_node_type: str | None,
    canvas: dict,
) -> list[CoachSuggestion]:
```

Each suggestion:

```python
@dataclass
class CoachSuggestion:
    node_type: str
    label: str
    reason: str
    prefilled_data: dict
```

### 6.1 Studio UI: Coach tab

Right column collapsible **Coach** panel (or bottom drawer on narrow screens):

- When node selected, show 3-5 suggestions
- Click **Add** -> creates node to the right of selection with auto-edge
- Empty selection: show "Start with Trigger + Agent task" hints

API (optional):

```
POST /api/playbooks/studio/coach
Body: { canvas, selected_node_id }
```

Can run client-side only if rules exported to `frontend/src/lib/playbook-studio/coachRules.ts` (duplicate rules ok for v1; prefer single Python source via API).

---

## 7. Extended canvas node types (v1)

Add to studio palette (233 node registry):

| Canvas type | YAML type | Notes |
| --- | --- | --- |
| `parallel` | `parallel` | Fan-out config (branch ids) |
| `artifact` | `artifact` | Export artifact step |
| `delay` | `wait` | Stub wait step (task fallback ok) |

Update `canvas_compiler.py` mappings. Decompiler support required.

---

## 8. Tests

`tests/playbook/test_variable_context.py`  
`tests/playbook/test_template_catalog.py`  
`tests/playbook/test_workflow_coach.py` - rule coverage per node type  
Roundtrip: template -> canvas -> yaml -> compile

---

## 9. Documentation

Update `docs/features/playbooks.md`:

- Variables section with examples
- Template gallery operator guide
- Coach panel screenshot placeholder

---

## 10. Acceptance criteria

| # | Test |
| --- | --- |
| 1 | Variables persist in YAML + canvas roundtrip |
| 2 | Run dialog collects variable overrides into initial_state |
| 3 | Template gallery lists >= 5 templates including aiva-deal-analyse |
| 4 | Use template loads canvas with nodes |
| 5 | Coach suggests >= 2 options after agent_task selected |
| 6 | parallel + artifact nodes compile through yaml_compiler |
| 7 | pytest passes |
| 8 | No Java coach code ported |

---

## 11. Out of scope

| Item | Prompt |
| --- | --- |
| ML-based coach | Future |
| File upload variable type | Future |
| Community template marketplace | 235 org feature |
| browser_action canvas node | Future |

---

## 12. Archive

`prompts-archive/237-template-variables-coach.md` when AC pass.
