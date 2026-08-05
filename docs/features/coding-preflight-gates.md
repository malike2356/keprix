# Coding preflight gates

Coding preflight runs before expensive code generation or scoped mutation work. It checks whether the repository context is ready, whether the task is duplicated, whether tests exist, whether the planned patch is too large, and whether provider budget pressure should change the model profile.

Reports are stored per session:

```text
{KEPRIX_HOME}/agent-os/preflight/<session_id>.json
```

## Gates

| Gate | Result |
| --- | --- |
| `repo_index` | Warns when repo map/context is missing |
| `duplicate_task` | Warns when the same task appears in the recent turn window |
| `test_exists` | Warns when nearby tests are not found |
| `diff_budget` | Blocks when planned patch lines exceed the configured limit |
| `provider_budget` | Warns when provider usage is near the configured threshold |

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/coding/preflight/run` | Run gates for a session |
| `GET` | `/api/coding/preflight/{session_id}` | Read the last report |
| `POST` | `/api/coding/preflight/{session_id}/override` | Apply operator override |
| `GET` | `/api/coding/preflight/config` | Read settings |
| `PUT` | `/api/coding/preflight/config` | Save settings |

Set `KEPRIX_CODING_PREFLIGHT=0` to disable gates. Disabled reports return `overall=proceed`.

## CLI

```bash
keprix coding preflight run --session <id> --intent "Add export" --repo /path/to/repo
keprix coding preflight show --session <id>
keprix coding preflight config
```

Reports with warnings or blocks write estimated token savings and triggered gates to the Agent OS run ledger as `source_type=coding_preflight`.
