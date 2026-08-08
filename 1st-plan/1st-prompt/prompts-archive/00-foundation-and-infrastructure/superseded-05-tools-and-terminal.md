# keprix - Prompt 05: Tools and Terminal Execution

## Context

Sources:
- `hermes-agent/tools/` - core tool implementations
- `hermes-agent/agent/tool_executor.py`, `tool_guardrails.py`, `tool_dispatch_helpers.py`
- `hermes-agent/agent/lsp/` - Language Server Protocol integration
- `core.carinaai.uk/src/tools/` - Carina's 71 tools (TypeScript reference; port logic to Python)
- `odysseus/routes/shell_routes.py` - Odysseus shell execution
Output: `keprix/backend/tools/`

## Hermes Tool Directory Port

Port verbatim from `hermes-agent/tools/`:
```
tools/                       -> backend/tools/
  computer_use/              -> backend/tools/computer_use/
  environments/              -> backend/tools/environments/
  neutts_samples/            -> backend/tools/neutts_samples/
```

## Core Tool Set (71 tools)

All 71 tools defined in `core.carinaai.uk/src/tools/` must be present in CE.
Read `TOOLSET_MAP` from `core.carinaai.uk/src/tools/index.ts` to get the full
list. For each tool that exists in Hermes (Python), port from there.
For tools in Aiva (commercial) (TypeScript) that have no Hermes equivalent,
implement a Python equivalent in `backend/tools/`.

The 71 tools are grouped in these toolsets. Implement all of them:

### Filesystem Tools
- read_file, write_file, edit_file, list_directory, search_files, find_files
- copy_file, move_file, delete_file, create_directory
- watch_file (file change notification)

### Shell / Terminal Tools
- run_command (bash execution with timeout, working directory, env)
- run_background (detached process, returns PID)
- kill_process, list_processes
- Sandbox modes: local, Docker container, SSH remote, Modal cloud
- Port `tools/environments/` Docker and SSH environment managers verbatim
- Port `odysseus/routes/shell_routes.py` shell execution with its path-confinement logic
  (tests: `odysseus/tests/test_workspace_confine.py`, `test_tool_path_confinement.py`)

### Web / Browser Tools
- web_fetch (HTTP GET with size caps, plaintext extraction)
  - Port Odysseus size cap logic from `tests/test_web_fetch_size_caps.py`
  - Port Odysseus URL safety from `tests/test_url_safety.py` (SSRF protection)
- web_search (SearXNG integration from Odysseus `config/searxng/`)
  - Also support: Exa, Parallel, Firecrawl, Tavily as alternative search backends
- browser_navigate, browser_click, browser_fill, browser_screenshot, browser_evaluate
  - Port Hermes `plugins/browser/` verbatim (see Prompt 07)

### Code / Development Tools
- read_code (language-aware), search_symbol, find_references
- lsp_hover, lsp_completion, lsp_diagnostics, lsp_goto_definition
  - Port `agent/lsp/` complete (client, manager, protocol, workspace, etc.)
- git_status, git_diff, git_log, git_commit, git_branch, git_push, git_pull
- run_tests, lint_code

### Research Tools
- deep_research (multi-step, see Prompt 14)
- summarize_url
- compare_models (blind A/B from Odysseus `routes/compare_routes.py`)
- youtube_transcript (port from Odysseus `routes/` YouTube handler)
  - Port tests: `tests/test_youtube_extract_id_nonstring.py`

### Memory / Knowledge Tools
- remember, recall, forget (episodic memory - see Prompt 06)
- rag_search (vector search - see Prompt 06)
- embed_document

### Communication Tools
- send_message (to any configured channel)
- send_email (via email integration - see Prompt 11)
- create_calendar_event, list_calendar_events (see Prompt 10)

### Productivity Tools
- create_note, list_notes, search_notes (see Prompt 10)
- create_task, list_tasks, complete_task (see Prompt 10)
- create_kanban_card, move_kanban_card (port from Hermes `plugins/kanban/`)

### Image / Media Tools
- generate_image (multi-provider, see Prompt 04)
- describe_image (vision model)
- edit_image (from Odysseus `routes/gallery_routes.py`)
- generate_video (from Hermes `plugins/video_gen/`)
- text_to_speech, speech_to_text (see Prompt 04)

### System Tools
- get_system_info, get_disk_usage
- list_installed_packages
- computer_use (port `tools/computer_use/` from Hermes)

## Tool Guardrail System

Port `agent/tool_guardrails.py` and `agent/tool_loop_guardrails.py` verbatim.

The guardrail system must:
- Detect infinite tool loops (same tool called with same args N times)
- Emit a warning after N=2 repeated failures (configurable)
- Hard-stop after configurable limit (default: off)
- Report loop state to the frontend via the API

## Tool Dispatch

`backend/tools/dispatcher.py` must:
- Register all 71 tools at startup
- Dispatch tool calls by name from the conversation loop
- Support `check_fn` guards (service-gated tools that only activate when a
  service is configured, e.g. web_search only if SEARXNG_URL or EXA_API_KEY set)
- Return `ToolResult` with `content`, `is_error`, `metadata` fields

## LSP Integration

Port `agent/lsp/` complete:
```
agent/lsp/client.py      -> backend/tools/lsp/client.py
agent/lsp/cli.py         -> backend/tools/lsp/cli.py
agent/lsp/eventlog.py    -> backend/tools/lsp/eventlog.py
agent/lsp/install.py     -> backend/tools/lsp/install.py
agent/lsp/manager.py     -> backend/tools/lsp/manager.py
agent/lsp/protocol.py    -> backend/tools/lsp/protocol.py
agent/lsp/range_shift.py -> backend/tools/lsp/range_shift.py
agent/lsp/reporter.py    -> backend/tools/lsp/reporter.py
agent/lsp/servers.py     -> backend/tools/lsp/servers.py
agent/lsp/workspace.py   -> backend/tools/lsp/workspace.py
```

Supported language servers (from Hermes `lsp/servers.py`): Python, TypeScript,
JavaScript, Rust, Go, Java, C/C++, PHP, Ruby, Kotlin, Swift.

## Odysseus Tool Additions

From Odysseus, extract and port these tool capabilities not present in Hermes:

1. `routes/compare_routes.py` - blind model A/B comparison (port as `tools/compare.py`)
2. `routes/vault_routes.py` - encrypted credential vault (port as `tools/vault.py`)
   - Use the test `tests/test_vault_password_not_in_argv.py` to verify security
3. `routes/contacts_routes.py` - contacts store (port as `tools/contacts.py`)
4. `routes/embedding_routes.py` - manual embedding trigger (port as `tools/embeddings.py`)
5. `routes/personal_routes.py` - personal data / user profile tools

## Security: SSRF and Path Confinement

Every tool that accepts a URL must pass through `tools/url_safety.py`:
- Port the SSRF protection from `odysseus/tests/test_url_safety.py`
- Block: localhost, 127.x, 169.254.x, 10.x, 172.16-31.x, ::1, metadata IPs
- Port `tests/test_webhook_ssrf_resilience.py` logic for webhook URL validation

Every tool that accepts a file path must pass through `tools/path_safety.py`:
- Port from `odysseus/tests/test_workspace_confine.py`
- Block traversal outside the workspace root

## Acceptance Criteria

- `from backend.tools.dispatcher import ToolDispatcher` imports clean
- `ToolDispatcher` has exactly 71+ registered tools at startup
- `run_command("echo hello")` returns `ToolResult(content="hello\n", is_error=False)`
- `web_fetch("http://169.254.169.254/")` returns an SSRF-blocked error, not content
- `read_file("../../etc/passwd")` returns a path-confinement error
- `lsp_diagnostics` returns empty list on a clean Python file
