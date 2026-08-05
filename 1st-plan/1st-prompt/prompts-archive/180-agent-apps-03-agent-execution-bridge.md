# Keprix Prompt 180: Agent Apps - Agent Execution Bridge

## Purpose

Make `runtime: agent` and `runtime: hybrid` manifests invoke the **real Keprix agent loop**
(instructions + tools + skills), not just a Python `entrypoint` greeting. This is the core
sellable capability: packaged agents that think and use tools.

Read reference **177**. Requires prompts **179** (manifest v2) and existing agent loop
(`keprix.agent`, chat pipeline, tool registry).

---

## Dependencies

- `src/keprix/agent_apps/runner_core.py`, `web_runner.py`, `local_runner.py`
- `src/keprix/agent_apps/lifecycle.py`
- Agent loop entry (grep `run_agent` / `AgentSession` in `src/keprix/`)
- `instructions.md` pattern in sample apps
- Vault: `src/keprix/vault/` for env resolution

---

## What to build

### 1. New module `agent_runtime.py`

```text
src/keprix/agent_apps/agent_runtime.py
```

```python
async def run_agent_app_llm(
    app_dir: Path,
    manifest: AgentAppManifest,
    *,
    inputs: dict[str, Any],
    context: dict[str, Any],
    user_id: str | None = None,
) -> AgentAppRunResult:
    """
    1. Load instructions.md
    2. Resolve required_env from vault/settings (fail fast with actionable message)
    3. Register manifest tools/playbooks into ephemeral run scope
    4. Invoke Keprix agent with user message built from inputs template
    5. Emit lifecycle events; return structured output + artifacts
    """
```

Do **not** duplicate LLM provider wiring; use configured `KEPRIX_DEFAULT_PROVIDER` and
existing provider factory.

### 2. Input to prompt template

Support optional `prompt_template.md` in app folder:

```markdown
Summarise standup for: {{focus}}
```

If missing, default: join `inputs` as key=value lines appended to instructions.

### 3. Permissions gate

Before run, check `required_permissions` against workspace policy:

| Permission | Behavior |
| --- | --- |
| `network` | Allow web/fetch tools |
| `email_read` | Enable email tools if configured |
| `filesystem` | Allow workspace file tools |

If denied, return lifecycle event `on_approval_requested` and HTTP 403 with UI message
"Enable email access in Settings" (link to `/settings`).

### 4. Wire runners

In `web_runner.py` / `runner_core.py`:

```python
if manifest.runtime in ("agent", "hybrid"):
    result = await run_agent_app_llm(...)
elif manifest.runtime == "python":
    result = run_python_entrypoint(...)
```

`hybrid`: run Python pre-hook if `pre_entrypoint` set (optional v2 field), then agent.

### 5. Vault pre-flight API

`GET /api/agent-apps/{name}/readiness`:

```json
{
  "ready": false,
  "missing_env": ["NOTION_TOKEN"],
  "missing_permissions": [],
  "vault_links": [{ "key": "NOTION_TOKEN", "href": "/vault?highlight=NOTION_TOKEN" }]
}
```

Frontend: block **Run** with inline wizard until `ready: true` (or user overrides admin-only).

### 6. Catalog app stubs (prepare for 182)

Create folder structure only (minimal manifests, full implementation in **182**):

```text
src/keprix/agent_apps/catalog/daily-standup/
src/keprix/agent_apps/catalog/research-brief/
```

Each: `agent.yaml` with `runtime: agent`, `instructions.md`, one tool yaml reference.

---

## Acceptance criteria

- [ ] Sample app with `runtime: agent` runs via web UI and returns LLM output.
- [ ] `required_env` missing returns readiness response, not opaque 500.
- [ ] Lifecycle traces include `before_run`, `after_run`, `on_error`.
- [ ] Python-only apps unchanged.
- [ ] Tests with mocked LLM: `tests/agent_apps/test_agent_runtime.py`.

---

## Out of scope

- Persistent trace DB (**185**)
- Scheduled cron (**183**)

---

## Archive

On completion: move to `prompts-archive/`.
