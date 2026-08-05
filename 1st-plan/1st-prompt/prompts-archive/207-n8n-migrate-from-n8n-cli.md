# Keprix - Prompt 207: n8n Workflow Import CLI (`migrate from-n8n`)

## Purpose

Close gap **N2** and **P0** from `planning/competitor-research/agents-to-adopt/n8n/GAPS-FOR-KEPRIX.md`.
`docs/features/migration.md` documents `keprix migrate from-n8n` but no converter exists.
Ship a **best-effort bridge** that maps common n8n export JSON to Keprix playbook YAML.
Do **not** port `nodes-base` or n8n runtime code (license boundary).

## Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Agent migration CLI pattern | `src/keprix/backend/migration/cli.py` (`migrate from`, `preview`, `apply`) |
| Playbook YAML schema docs | `docs/features/playbooks.md` |
| Playbook runtime | `src/keprix/playbook/runtime/` |
| n8n fixture JSON (reference only) | `planning/competitor-research/agents-to-adopt/n8n/packages/testing/playwright/workflows/*.json` |

## Gap

No `from-n8n` subcommand. Operators cannot import exported n8n workflows.

## Working directory

`/opt/lampp/htdocs/verlox/keprix/`

## Reference

- Gap register: `planning/competitor-research/agents-to-adopt/n8n/GAPS-FOR-KEPRIX.md` (P0)
- Sample HTTP workflow: `.../n8n/.../Simple_workflow_with_http_node.json`
- Sample If/Code workflow: `.../n8n/.../Workflow_if.json`
- Target playbook shape: `docs/features/playbooks.md` (`steps`, `edges`, step types)

## Step 1: Converter module

Create `src/keprix/backend/migration/n8n_converter.py`:

```python
@dataclass
class N8nConversionResult:
    playbook_id: str
    name: str
    yaml_text: str
    mapped_nodes: list[str]
    skipped_nodes: list[dict[str, str]]  # name, type, reason
    warnings: list[str]

def load_n8n_export(path: Path) -> dict[str, Any]: ...
def convert_n8n_workflow(payload: dict[str, Any], *, playbook_id: str | None = None) -> N8nConversionResult: ...
```

### Supported n8n node types (v1)

| n8n `type` | Keprix step `type` | Mapping rules |
| --- | --- | --- |
| `n8n-nodes-base.httpRequest` | `http` | `url`, method (default GET), query/body as JSON; strip `={{ }}` expressions to `{{ n8n_expr:... }}` comment placeholders |
| `n8n-nodes-base.code` | `code` | `parameters.jsCode` or `pythonCode` into `source`; language tag |
| `n8n-nodes-base.if` | `condition` | Flatten first condition to `expression` string with TODO comment if n8n expression not translatable |
| `n8n-nodes-base.set` | `code` | Emit Python dict merge stub or `agent_task` with "set fields" prompt |
| `n8n-nodes-base.manualTrigger` | (metadata) | Becomes playbook `description` note only |
| `n8n-nodes-base.scheduleTrigger` | (metadata) | Add top comment: "Schedule via Keprix cron or agent-apps" |
| `n8n-nodes-base.webhook` | `http` stub | Comment: replace with Keprix webhook trigger route |

### Connection mapping

- Walk `connections.main` arrays; build `edges: [{from, to}]` using node **names** slugified to step `id` (kebab-case, max 48 chars).
- Preserve execution order; parallel branches become multiple edges from same `from`.

### Skipped nodes

Any other `type` goes to `skipped_nodes` with reason `unsupported_node_type`.
Append YAML header comment block listing skipped nodes and review URLs.

## Step 2: CLI wiring

Extend `src/keprix/backend/migration/cli.py`:

```bash
keprix migrate from-n8n --source /path/to/workflow.json --output .keprix/playbooks/imported.yml
keprix migrate from-n8n --source /path/to/workflow.json --output-dir .keprix/playbooks/ --dry-run
```

Register in `register_migrate_agent_subparsers` **or** add sibling parser `from-n8n` under `migrate` (match docs exactly):

```bash
python3 -m keprix.keprix_cli.main migrate from-n8n --source n8n-export.json --output .keprix/playbooks/
```

Flags:

| Flag | Behavior |
| --- | --- |
| `--source` | Path to n8n workflow JSON (single workflow object or `{ "nodes", "connections" }`) |
| `--output` | Write one `.yml` file |
| `--output-dir` | Write `{playbook_id}.yml` into directory |
| `--id` | Override playbook id slug |
| `--dry-run` | Print YAML + summary to stdout; do not write |
| `--report` | Also write `{playbook_id}.migration-report.json` with skipped_nodes |

Wire through `keprix_cli/main.py` migrate subparser (alongside existing `from hermes|openclaw|...`).

## Step 3: Fixtures and tests

Add `tests/migration/fixtures/n8n/`:

- `simple_http.json` (copy minimal fields from vendored Simple_workflow_with_http_node.json)
- `if_code_chain.json` (subset of Workflow_if.json)

Add `tests/migration/test_n8n_converter.py`:

1. HTTP workflow produces one `http` step and one edge
2. If node produces `condition` step or documented skip
3. Code node preserves source text
4. Unknown node type appears in `skipped_nodes`, YAML still valid
5. CLI dry-run exits 0

Use `.venv/bin/python -m pytest tests/migration/test_n8n_converter.py`.

## Step 4: Docs

Update `docs/features/migration.md` n8n section:

- Document exact CLI command and flags
- State **best-effort** scope and link to migration report JSON
- Note: complex n8n expressions need manual edit; use `keprix mcp install n8n` for live n8n sidecar (Prompt 210)

## Acceptance criteria

| # | Test |
| --- | --- |
| 1 | `convert_n8n_workflow` maps HTTP + connections to valid playbook YAML |
| 2 | Skipped nodes listed in report; YAML includes review comment header |
| 3 | `keprix migrate from-n8n --dry-run` prints YAML without error |
| 4 | `pytest tests/migration/test_n8n_converter.py` passes |
| 5 | `docs/features/migration.md` matches implemented CLI |
| 6 | No code copied from vendored n8n tree into `src/keprix/` |

## Archive

`prompts-archive/` when AC pass.
