# Keprix - Prompt 211: Playbook Expression Sandbox Hardening

## Purpose

Close gap **P4** (#8 in capability matrix) from `planning/competitor-research/agents-to-adopt/n8n/GAPS-FOR-KEPRIX.md`.
Study n8n `expression-runtime` isolation ideas. Harden Keprix playbook **condition** expressions and
HTTP/body template interpolation so user YAML cannot execute arbitrary Python.

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Playbook condition docs | `docs/features/playbooks.md` (`expression: "steps.triage.output.urgency == 'high'"`) |
| Edge conditions in graph runtime | `src/keprix/playbook/runtime/edge.py` |
| SDK workflow branch `when` | `src/keprix/playbook/sdk_workflow.py` |
| Research sandbox denylist | `src/keprix/research_workspace/notebooks/sandbox.py` (`eval` blocked) |

## Gap

Condition and template evaluation may use unsafe `eval()` or ad-hoc parsing (verify during implementation).
No single restricted expression evaluator for playbook YAML.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Reference (read only)

- `planning/competitor-research/agents-to-adopt/n8n/packages/@n8n/expression-runtime/`
- `planning/competitor-research/agents-to-adopt/n8n/GAPS-FOR-KEPRIX.md` (P4)

## Step 1: Safe expression module

Create `src/keprix/playbook/expression_sandbox.py`:

```python
class ExpressionError(ValueError): ...

ALLOWED_OPS = ...  # ast.Eq, Lt, Gt, And, Or, Not, In, etc.
ALLOWED_NAMES = {"steps", "state", "true", "false", "null"}

def evaluate_condition(expression: str, context: dict[str, Any]) -> bool: ...
def render_template(template: str, context: dict[str, Any]) -> str: ...
```

Rules:

1. Parse with `ast.parse(expression, mode="eval")`; walk tree; reject `Call`, `Attribute` beyond `steps.foo.bar`, `Import`, `Lambda`, comprehensions
2. Support literals, `==`, `!=`, `<`, `>`, `in`, `and`, `or`, `not`
3. Resolve `steps.<id>.output.<path>` from context dict only (no getattr on arbitrary objects)
4. `render_template`: replace `{{ steps.id.output }}` and `{{ state.key }}` via regex + sandbox resolver; leave unknown tokens as empty string + warning log
5. **Never** call bare `eval()` on user strings

Add comprehensive unit tests in `tests/playbook/test_expression_sandbox.py`:

- Allowed expressions pass
- `__import__('os')`, `open(`, attribute on builtins fail
- Template render with nested dict paths

## Step 2: Wire playbook YAML runtime

Find playbook step handlers for `type: condition` and HTTP body/url templates (grep `playbook` + `condition`).

Replace any unsafe eval with `evaluate_condition` / `render_template`.

For SDK workflow `when: "true"` string edges in `sdk_workflow.py`, route string conditions through same evaluator with `state` context.

On `ExpressionError`, fail step with `NODE_FAILED` event carrying `error: "invalid_expression"`.

## Step 3: Docs and operator messaging

Update `docs/features/playbooks.md` condition section:

- Document supported expression subset (no function calls)
- Show `{{ steps.fetch.output.field }}` template syntax for `agent_task` prompts
- Note: n8n `={{ $json }}` is **not** supported; use Prompt 207 import placeholders

## Step 4: Migration converter alignment

In Prompt 207 converter (if shipped), map obvious n8n expressions to comments:

`={{ $json.data }}` -> `# TODO: replace with {{ steps.<prev>.output.data }}`

If 207 not merged yet, add note in this prompt's tests only.

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | `evaluate_condition` rejects injection attempts in `tests/playbook/test_expression_sandbox.py` |
| 2 | Valid playbook condition step routes correctly in runtime integration test |
| 3 | `render_template` resolves `{{ steps.x.output }}` in agent_task prompt |
| 4 | No bare `eval(user_input)` in `src/keprix/playbook/` (grep CI check in test optional) |
| 5 | `pytest tests/playbook/` passes |

## Archive

`prompts-archive/` when AC pass.
