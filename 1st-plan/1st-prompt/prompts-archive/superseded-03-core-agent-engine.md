# keprix - Prompt 03: Core Agent Engine (Hermes Spine)

## Context

Read `00a-product-vision-and-agent-consolidation-map.md` for the consolidation model.

Hermes Agent is the **spine** of keprix. Every other adopted agent plugs into this core.
This prompt ports the Hermes agent core verbatim into keprix, then applies the full rename
table. Do not refactor logic in the first pass. Do not add features. Copy, rename, wire.

Source: `planning/agents-to-adopt/hermes-agent/` (Python)
Output: `keprix/backend/agent/`

## Source Files to Port

Port every file in these Hermes directories:

```
agent/conversation_loop.py         -> backend/agent/conversation_loop.py
agent/run_agent.py (root)          -> backend/agent/run_agent.py
agent/agent_init.py                -> backend/agent/agent_init.py
agent/agent_runtime_helpers.py     -> backend/agent/agent_runtime_helpers.py
agent/context_compressor.py        -> backend/agent/context_compressor.py
agent/context_engine.py            -> backend/agent/context_engine.py
agent/context_references.py        -> backend/agent/context_references.py
agent/conversation_compression.py  -> backend/agent/conversation_compression.py
agent/prompt_builder.py            -> backend/agent/prompt_builder.py
agent/prompt_caching.py            -> backend/agent/prompt_caching.py
agent/system_prompt.py             -> backend/agent/system_prompt.py
agent/tool_executor.py             -> backend/agent/tool_executor.py
agent/tool_dispatch_helpers.py     -> backend/agent/tool_dispatch_helpers.py
agent/tool_guardrails.py           -> backend/agent/tool_guardrails.py
agent/tool_result_classification.py -> backend/agent/tool_result_classification.py
agent/tool_loop_guardrails.py      -> backend/agent/tool_loop_guardrails.py
agent/iteration_budget.py          -> backend/agent/iteration_budget.py
agent/error_classifier.py          -> backend/agent/error_classifier.py
agent/errors.py                    -> backend/agent/errors.py
agent/retry_utils.py               -> backend/agent/retry_utils.py
agent/rate_limit_tracker.py        -> backend/agent/rate_limit_tracker.py
agent/message_sanitization.py      -> backend/agent/message_sanitization.py
agent/think_scrubber.py            -> backend/agent/think_scrubber.py
agent/title_generator.py           -> backend/agent/title_generator.py
agent/trajectory.py                -> backend/agent/trajectory.py
agent/display.py                   -> backend/agent/display.py
agent/background_review.py         -> backend/agent/background_review.py
agent/insights.py                  -> backend/agent/insights.py
agent/manual_compression_feedback.py -> backend/agent/manual_compression_feedback.py
agent/coding_context.py            -> backend/agent/coding_context.py
agent/subdirectory_hints.py        -> backend/agent/subdirectory_hints.py
agent/file_safety.py               -> backend/agent/file_safety.py
agent/runtime_cwd.py               -> backend/agent/runtime_cwd.py
agent/async_utils.py               -> backend/agent/async_utils.py
agent/markdown_tables.py           -> backend/agent/markdown_tables.py
agent/stream_diag.py               -> backend/agent/stream_diag.py
agent/shell_hooks.py               -> backend/agent/shell_hooks.py
agent/i18n.py                      -> backend/agent/i18n.py
agent/onboarding.py                -> backend/agent/onboarding.py
hermes_state.py                    -> backend/agent/state.py
hermes_constants.py                -> backend/agent/keprix_constants.py
hermes_logging.py                  -> backend/agent/logging.py
hermes_time.py                     -> backend/agent/time_utils.py
hermes_bootstrap.py                -> backend/agent/bootstrap.py
hermes_cli/ (whole dir)            -> backend/cli/
run_agent.py (root)                -> backend/run_agent.py
utils.py                           -> backend/utils.py
toolsets.py                        -> backend/toolsets.py
toolset_distributions.py           -> backend/toolset_distributions.py
model_tools.py                     -> backend/model_tools.py
batch_runner.py                    -> backend/batch_runner.py
trajectory_compressor.py           -> backend/trajectory_compressor.py
```

Also port these Hermes agent sub-packages verbatim:
```
agent/lsp/          -> backend/agent/lsp/
agent/transports/   -> backend/agent/transports/
agent/secret_sources/ -> backend/agent/secret_sources/
```

## Renames to Apply Across All Ported Files

After copying, do a project-wide search-and-replace on the ported files only:

| Find | Replace |
|---|---|
| `hermes` (lowercase, as identifier/string) | `keprix` |
| `Hermes` (capitalized, in strings/comments) | `Keprix` |
| `HERMES` (all caps, as constant prefix) | `KEPRIX` |
| `hermes_state` | `keprix_state` |
| `hermes_constants` | `keprix_constants` |
| `hermes-agent` (in strings) | `keprix` |
| `~/.hermes/` | `~/.keprix/` |
| `HERMES_` (env var prefix) | `KEPRIX_` |

Do NOT rename Python stdlib references, third-party package names, or model
provider names that happen to contain these strings.

## Config Directory

Port Hermes config files:
```
cli-config.yaml.example -> keprix/backend/config/config.example.yaml
```

Replace all `hermes` references in the config file with `keprix` / `keprix`.

## Entry Points

Create `keprix/backend/main.py`:
```python
from agent.bootstrap import bootstrap
from run_agent import run

if __name__ == "__main__":
    bootstrap()
    run()
```

Create `keprix/backend/__init__.py` with version:
```python
__version__ = "1.0.0"
__edition__ = "community"
```

## Locales

Port `hermes-agent/locales/` verbatim to `keprix/backend/locales/`.
In each locale file, replace "Hermes" display strings with "Keprix".

## Tests

Port `hermes-agent/tests/` verbatim to `keprix/backend/tests/`.
Update all import paths from `hermes.*` / `hermes_*` to `keprix.*` / `keprix_*`.
Do not change test logic.

## Acceptance Criteria

- `cd keprix && python -c "from backend.agent.conversation_loop import ConversationLoop"` imports without error
- `cd keprix && python -c "from backend.agent.keprix_constants import PRODUCT_NAME"` returns "keprix"
- `grep -r "Hermes" backend/agent/ | grep -v ".pyc"` returns zero matches in string literals
- `grep -r "~/.hermes" backend/` returns zero matches
- All test files in `backend/tests/` parse without syntax errors (`python -m py_compile`)
