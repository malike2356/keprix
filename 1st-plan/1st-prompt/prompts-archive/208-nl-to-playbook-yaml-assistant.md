# Keprix - Prompt 208: NL to Playbook YAML Assistant

## Purpose

Close gap **P1** and **N6** from `planning/competitor-research/agents-to-adopt/n8n/GAPS-FOR-KEPRIX.md`.
Study n8n `ai-workflow-builder.ee` eval patterns; ship Keprix-native **natural language to playbook YAML**
(not a visual canvas). Wire into `/playbooks` Start dialog and optional API for agent-studio.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Playbook runtime + templates | `src/keprix/playbook/graph_catalog.py`, `run_routes.py` |
| Start run dialog | `frontend/src/components/playbooks/StartPlaybookDialog.tsx` |
| Playbook docs / schema | `docs/features/playbooks.md` |
| Eval harness patterns | `src/keprix/evals/`, `evals/suites/` |

## Gap

Operators cannot describe a workflow in plain language and get editable playbook YAML.
n8n ships AI workflow builder with eval harness; Keprix has templates only.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Reference (read only, do not copy code)

- `planning/competitor-research/agents-to-adopt/n8n/packages/@n8n/ai-workflow-builder.ee/evaluations/README.md`
- `planning/competitor-research/agents-to-adopt/n8n/GAPS-FOR-KEPRIX.md`

## Step 1: Backend generation API

Create `src/keprix/playbook/nl_builder.py`:

```python
class PlaybookDraftRequest(BaseModel):
    prompt: str
    workspace_id: str = "default"
    template_hint: str | None = None  # optional graph_id to extend

class PlaybookDraftResult(BaseModel):
    yaml_text: str
    playbook_id: str
    warnings: list[str]
    model_id: str

async def generate_playbook_yaml(request: PlaybookDraftRequest) -> PlaybookDraftResult: ...
```

System prompt rules (hard-code in module):

1. Output **only** valid playbook YAML matching `docs/features/playbooks.md` step types
2. Prefer `agent_task`, `http`, `condition`, `human_approval` over exotic types
3. Include `id`, `name`, `description`, `steps`, `edges`
4. Use `{{ steps.<id>.output }}` for cross-step references (not n8n `={{ $json }}`)
5. If prompt implies schedule, add YAML comment pointing to cron admin
6. Never invent tool names not in registry; use generic `tools: []` with comment

Add route `src/keprix/playbook/nl_builder_routes.py`:

```python
POST /api/playbooks/draft-from-prompt
Body: PlaybookDraftRequest
Response: PlaybookDraftResult
```

Register router in main API app. Require session auth (`useRequireSession` parity on backend).

Validate output with existing playbook YAML parser if present; on parse error return 422 with `warnings`.

## Step 2: Frontend "Describe" tab

Extend `StartPlaybookDialog.tsx`:

| Tab | Label | Behavior |
| --- | --- | --- |
| 0 | Template | (existing) |
| 1 | Describe | Multiline prompt + "Generate YAML" button |
| 2 | Advanced | (existing JSON/spec editor) |

Describe tab flow:

1. User enters prompt (placeholder: "Every morning, fetch unread email and post a digest note")
2. Call `POST /api/playbooks/draft-from-prompt`
3. Show generated YAML in read-only `CodeBlock` with "Edit in Advanced" button
4. "Start run" parses YAML from Advanced tab or posts `steps`/`edges` extracted server-side

Add `frontend/src/lib/playbook-draft-api.ts`:

```typescript
export async function draftPlaybookFromPrompt(body: {
  prompt: string;
  template_hint?: string;
}): Promise<{ yaml_text: string; playbook_id: string; warnings: string[] }>;
```

## Step 3: Eval fixtures (mandatory before GA)

Add `evals/suites/playbook/nl_draft_basics.yaml`:

```yaml
suite: playbook_nl_draft
cases:
  - id: daily_digest
    prompt: "Read email and write a daily digest note"
    must_include_steps: [agent_task]
    must_include_keys: [fetch, digest]
  - id: http_poll
    prompt: "GET status API every run and branch on 500 errors"
    must_include_steps: [http, condition]
```

Add `evals/playbook/validators.py` helper `validate_draft_yaml(yaml_text, case)`:

- Parse YAML
- Assert required step types and id substrings
- No `n8n-nodes-base` strings in output

Add `tests/playbook/test_nl_builder.py` with mocked LLM returning fixture YAML.

## Step 4: Docs

Add section to `docs/features/playbooks.md`: **Generate from description** (`/playbooks` > Start run > Describe).

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | `POST /api/playbooks/draft-from-prompt` returns parseable YAML for fixture prompt (mocked LLM) |
| 2 | `/playbooks` Describe tab generates YAML and can start a run |
| 3 | `evals/suites/playbook/nl_draft_basics.yaml` runs in eval harness or dedicated pytest |
| 4 | Generated YAML uses Keprix `{{ steps.* }}` style, not n8n expressions |
| 5 | `pytest tests/playbook/test_nl_builder.py` passes |
| 6 | Operator copy says "playbook" not "workflow" or "recipe" |

## Archive

`prompts-archive/` when AC pass.
