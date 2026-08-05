# Keprix Prompt 179: Agent Apps - Manifest v2 and Dynamic Forms

## Purpose

Extend `agent.yaml` with **operator-friendly metadata and typed inputs** so the UI renders
forms automatically (no freeform-only text box). Backward compatible with v1 manifests.

Read reference **177**. Requires prompt **178** (detail page shell).

---

## Dependencies

- `src/keprix/agent_apps/app_manifest.py`
- `src/keprix/agent_apps/sample/hello_agent/agent.yaml`
- `frontend/src/components/agent-apps/AgentAppDetail.tsx`

---

## What to build

### 1. Manifest schema v2

Extend `app_manifest.py` Pydantic models:

```yaml
# agent.yaml (v2 fields optional)
name: daily-standup
version: 1.0.0
display_name: Daily Standup          # NEW
description: One-line for cards      # NEW
category: productivity               # NEW enum: productivity | research | finance | custom
icon: standup                        # NEW optional slug
runtime: python                      # NEW: python | agent | hybrid (default python)
entrypoint: agents.main:run
inputs:                              # NEW
  - id: focus
    label: What should I focus on?
    type: text                       # text | textarea | select | boolean | number | file
    required: false
    default: ""
    placeholder: Optional hint
    options: []                      # for select
outputs:                             # NEW
  - id: markdown
    type: markdown                   # markdown | text | json | file
required_env: []
required_permissions: []
tools: []
playbooks: []
eval_suite: evals/basic.yaml
```

Validation rules:

- `name`: kebab-case, unique at install time
- `inputs[].id`: unique within manifest
- `runtime: agent` requires `instructions.md` to exist
- v1 manifests without new fields: synthesize `display_name` from `name`, empty `inputs`

### 2. API changes

`GET /api/agent-apps` and `GET /api/agent-apps/{name}` return:

```json
{
  "name": "hello-agent",
  "display_name": "Hello Agent",
  "description": "...",
  "category": "custom",
  "icon": null,
  "version": "1.0.0",
  "runtime": "python",
  "inputs": [...],
  "outputs": [...],
  "required_env": [],
  "required_permissions": []
}
```

`POST /{name}/run` body extended (backward compatible):

```json
{
  "input": "legacy string",
  "inputs": { "focus": "Q3 goals" },
  "context": {},
  "runner": "web"
}
```

Runner merges `inputs` into `context["form"]` and passes to entrypoint. If only `input` sent,
map to first text input or legacy behavior.

### 3. Frontend: `AgentAppRunForm`

New component:

```text
frontend/src/components/agent-apps/AgentAppRunForm.tsx
```

- Renders fields from `inputs[]` using MUI `TextField`, `Select`, `Switch`, `Checkbox`.
- Client-side required validation before submit.
- Submit calls `runAgentApp(name, { inputs: values })`.

Replace freeform-only field on detail page when `inputs.length > 0`.

### 4. Output rendering

`AgentAppOutput.tsx`:

- If manifest declares `outputs[0].type === markdown`, render with existing markdown component.
- If `file`, show download link when run result includes `artifact_path` or `artifacts[]`.
- Fallback: pretty-print JSON.

### 5. Update hello-agent sample

Add minimal v2 fields to sample `agent.yaml` and one input `name` so UI can be tested without
waiting for catalog templates.

---

## Acceptance criteria

- [ ] v1 manifests still install and run.
- [ ] v2 manifest validates; invalid `inputs` rejected at install.
- [ ] Detail page renders dynamic form from manifest.
- [ ] Run payload includes structured `inputs`.
- [ ] Tests: `tests/agent_apps/test_manifest.py` covers v2 fields and defaults.

---

## Out of scope

- LLM `runtime: agent` execution (**180**)
- Vault pre-check for `required_env` (**180**)

---

## Archive

On completion: move to `prompts-archive/`.
