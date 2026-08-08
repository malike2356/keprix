# Keprix - Prompt 150: Tool Synthesis Engine

## Purpose

Build the core tool synthesis capability: when the agent detects it lacks a tool,
it generates the tool's Python source via LLM, validates it in a sandbox, infers
its JSON schema, persists it to disk and database, and hot-loads it into the live
registry. After this prompt, Keprix can write new tools and use them immediately -
within the same session and in all future sessions.

This is the foundation of Tier 1 mutation. Prompt 151 wires the trigger path
(gap detection -> this synthesizer). Build this one first.

---

## Dependencies

| Prompt | Capability needed |
|---|---|
| 149 | Architecture reference and mutation store schema |
| 55 | `code_execution_tool.py` sandbox (subprocess execution environment) |
| existing | `tools/registry.py` with `reload_generated_tools()` and `toolset="generated"` |
| existing | `improvement/tool_gap_detector.py` produces `ToolGapProposal` |

---

## What to Build

### 1. `src/keprix/mutation/schema_inference.py`

Infer a complete Keprix tool JSON schema from a Python function's signature and
docstring. This eliminates the need for the synthesizer to also write schema JSON
(separating concerns and reducing LLM errors).

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class InferredSchema:
    name: str
    description: str
    input_schema: dict   # JSON Schema object
    errors: list[str]    # non-empty means inference failed

def infer_schema(source_code: str, function_name: str) -> InferredSchema:
    """
    Parse the Python source, find function_name, extract its signature
    and docstring, and produce a JSON Schema object suitable for
    registry.register(). Uses ast module only - no exec, no import.

    Type annotation -> JSON Schema type mapping:
      str       -> {"type": "string"}
      int       -> {"type": "integer"}
      float     -> {"type": "number"}
      bool      -> {"type": "boolean"}
      list      -> {"type": "array"}
      dict      -> {"type": "object"}
      None/Any  -> {} (no type constraint)
      Optional[X] -> X schema (mark as not required)

    Docstring lines starting with "Args:" or param names followed by ":"
    are parsed as parameter descriptions.

    Returns InferredSchema with errors if function not found or signature
    cannot be mapped. Caller decides whether to proceed with partial schema
    or reject the synthesis.
    """
```

### 2. `src/keprix/mutation/tool_sandbox.py`

Run generated tool source in a subprocess with strict resource limits and verify
it registers correctly without side effects.

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SandboxResult:
    passed: bool
    error: str | None          # None on pass
    stderr: str
    stdout: str
    duration_ms: int
    schema_valid: bool         # registry.register() was called with valid schema
    detected_function_name: str | None

def validate_tool_in_sandbox(
    source_code: str,
    tool_name: str,
    timeout_seconds: int = 10,
    memory_limit_mb: int = 128,
) -> SandboxResult:
    """
    Write source_code to a temp file.
    Execute in a subprocess with:
      - resource limits: CPU time, memory, no network (subprocess env stripped)
      - a mock registry that records register() calls without side effects
      - sys.path includes keprix stubs for common imports
    Verify:
      1. No exception on import/exec
      2. registry.register() was called exactly once
      3. The registered schema has a non-empty "name" and "description"
      4. The handler function exists and is callable
      5. Calling handler with an empty JSON input string does not crash
         (the tool must handle malformed input gracefully)
    Return SandboxResult. Never raise - always return a result.
    """

def _build_sandbox_harness() -> str:
    """Return the Python source for the mock registry harness injected into sandbox."""
```

The sandbox harness must:
- Define a `registry` object with a `.register()` method that records calls
- Intercept `import keprix` and substitute stubs for common keprix utilities
- Capture stdout/stderr without letting the tool write to the real filesystem
- Set `KEPRIX_SANDBOX=true` in the subprocess env so tools can detect sandbox mode

### 3. `src/keprix/mutation/tool_synthesizer.py`

The LLM-based tool code generator.

```python
from dataclasses import dataclass
from keprix.improvement.tool_gap_detector import ToolGapProposal
from keprix.mutation.tool_sandbox import SandboxResult
from keprix.mutation.schema_inference import InferredSchema

TOOL_SYNTHESIS_SYSTEM_PROMPT = """
You are a Keprix tool engineer. Your job is to write a single Python tool module
that Keprix can load into its live tool registry.

A Keprix tool module must:
1. Import `from tools.registry import registry` at the top.
2. Define exactly one handler function with this signature:
   def handle_{tool_name}(input_str: str) -> str:
       ...
   The handler receives a JSON string and must return a JSON string.
   Always parse input with json.loads(input_str) inside a try/except.
   Always return json.dumps(result, ensure_ascii=False).
3. Call registry.register() at module level (not inside a function):
   registry.register(
       name="{tool_name}",
       description="...",
       handler=handle_{tool_name},
       input_schema={ ... JSON Schema ... },
       toolset="generated",
   )
4. Use only Python standard library, keprix built-ins, and packages already
   in the keprix virtualenv. Do not import third-party packages not in requirements.
5. Handle all error cases. Return {"error": "..."} JSON on failure, never raise.
6. The module must be self-contained. No side effects on import.
7. No hardcoded secrets, credentials, or API keys. Use os.environ.get().

Write ONLY the Python source. No markdown, no explanation, no code fences.
"""

@dataclass
class SynthesisResult:
    success: bool
    tool_name: str
    source_code: str
    inferred_schema: InferredSchema | None
    sandbox_result: SandboxResult | None
    error: str | None
    attempts: int
    tokens_used: int

async def synthesize_tool(
    proposal: ToolGapProposal,
    workspace_id: str,
    max_attempts: int = 3,
    model: str | None = None,   # None = use workspace default
) -> SynthesisResult:
    """
    Generate Python tool source for the given gap proposal.

    Algorithm:
    1. Build a synthesis prompt from the proposal (tool_name, description,
       any example inputs/outputs from the run that triggered the gap).
    2. Call LLM with TOOL_SYNTHESIS_SYSTEM_PROMPT.
    3. Run infer_schema() on the result.
    4. Run validate_tool_in_sandbox() on the result.
    5. If sandbox fails, feed the error back to the LLM and retry
       (up to max_attempts total).
    6. Return SynthesisResult. Never raise.

    If all attempts fail, return SynthesisResult(success=False, error=...).
    """

def _build_synthesis_user_prompt(proposal: ToolGapProposal) -> str:
    """
    Build the user-facing synthesis prompt from a gap proposal.
    Include: tool name, description, example task that triggered the gap,
    any error messages from the failed run.
    """

def _extract_source_from_response(llm_response: str) -> str:
    """
    Strip markdown code fences if present. Return clean Python source.
    """
```

### 4. `src/keprix/mutation/store.py` (partial - tool persistence only for this prompt)

Persist synthesized tools to database and disk.

```python
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

@dataclass
class MutationRecord:
    id: str
    recorded_at: datetime
    workspace_id: str
    tier: str
    trigger: str
    status: str
    name: str
    description: str | None
    source_code: str | None
    approved_by: str | None
    approved_at: datetime | None
    quality_score: float | None
    use_count: int
    metadata: dict

class MutationStore:
    """
    Persistence layer for all mutation events.
    Backed by the mutation_events and mutation_quality_samples tables
    from the migration in Prompt 149.

    For this prompt, implement only the tool-related methods:
      - save_generated_tool()
      - get_generated_tool()
      - list_generated_tools()
      - update_status()
      - write_tool_to_disk()
      - load_tools_on_startup()
    """

    def save_generated_tool(
        self,
        workspace_id: str,
        tool_name: str,
        description: str,
        source_code: str,
        trigger: str,
        confidence: float,
        auto_approve_threshold: float,
    ) -> MutationRecord:
        """
        Insert a row into mutation_events with tier="tool".
        Set status="approved" if confidence >= auto_approve_threshold,
        else status="staged" (awaiting operator approval).
        Return the saved record.
        """

    def write_tool_to_disk(self, record: MutationRecord, generated_dir: Path) -> Path:
        """
        Write record.source_code to generated_dir/{tool_name}.py.
        Return the path. Atomic write (write to .tmp, rename).
        Only call this for approved records.
        """

    def load_tools_on_startup(self, workspace_id: str, generated_dir: Path) -> int:
        """
        Called at Keprix startup. Query all mutation_events where
        tier="tool" AND status="approved". Write each to disk.
        Call registry.reload_generated_tools(generated_dir).
        Return count of loaded tools.
        """
```

### 5. Database migration

`migrations/versions/015_mutation_store.py`

Create the full schema from Prompt 149:
- `mutation_events`
- `mutation_quality_samples`

Both tables. All indexes. Use the same Alembic pattern as existing migrations.

### 6. Startup wiring

`src/keprix/run_agent.py` or the appropriate startup entrypoint:

At startup, after the registry is initialized:
```python
if settings.mutation_enabled and settings.mutation_tool_synthesis:
    generated_dir = Path(settings.mutation_generated_tools_dir).expanduser()
    generated_dir.mkdir(parents=True, exist_ok=True)
    count = mutation_store.load_tools_on_startup(workspace_id, generated_dir)
    if count:
        logger.info("Loaded %d generated tools from mutation store", count)
```

### 7. Configuration additions to `config/settings.py` or equivalent

```python
mutation_enabled: bool = False
mutation_tool_synthesis: bool = False
mutation_prompt_evolution: bool = False
mutation_self_coding: bool = False
mutation_auto_approve_threshold: float = 0.85
mutation_require_tests: bool = True
mutation_generated_tools_dir: str = "~/.keprix/generated_tools"
mutation_retention_days: int = 365
mutation_max_generated_tools: int = 200
mutation_prune_after_days: int = 90
```

---

## Acceptance Criteria

1. Given a `ToolGapProposal` with `tool_name="fetch_weather"` and
   `description="Fetches current weather for a city from a free API"`,
   `synthesize_tool()` returns `SynthesisResult(success=True)` with valid Python
   source that passes sandbox validation.

2. `validate_tool_in_sandbox()` returns `SandboxResult(passed=True)` for a
   correct tool and `SandboxResult(passed=False, error=...)` for a tool that
   raises an exception on import.

3. `infer_schema()` correctly maps `str, int, bool` parameters to JSON Schema
   types without executing the code.

4. `MutationStore.save_generated_tool()` with confidence 0.9 and threshold 0.85
   writes a row with `status="approved"`. With confidence 0.7, writes `status="staged"`.

5. `MutationStore.load_tools_on_startup()` writes `.py` files to disk and
   `registry.reload_generated_tools()` makes them available via
   `registry.get_tools_by_toolset("generated")`.

6. After `load_tools_on_startup()`, calling `run_agent.py` with a task that would
   use the generated tool succeeds without a `ModuleNotFoundError`.

7. A synthesized tool that fails sandbox validation is NOT persisted and NOT
   added to the registry. The `SynthesisResult.error` describes why.

8. If the LLM produces code with a syntax error, `synthesize_tool()` retries up
   to `max_attempts` times feeding the error back as context.

---

## Tests

### `tests/mutation/test_schema_inference.py`

```python
def test_infers_str_int_bool_params()
def test_infers_optional_param_not_required()
def test_extracts_description_from_docstring()
def test_returns_errors_when_function_not_found()
def test_no_exec_during_inference()
```

### `tests/mutation/test_tool_sandbox.py`

```python
def test_valid_tool_passes()
def test_syntax_error_fails()
def test_import_error_fails()
def test_tool_that_raises_on_call_fails()
def test_tool_with_no_register_call_fails()
def test_timeout_respected()
def test_no_filesystem_write_allowed()
def test_no_network_access_allowed()
```

### `tests/mutation/test_tool_synthesizer.py`

```python
def test_synthesize_simple_tool_returns_valid_source(mock_llm)
def test_retries_on_sandbox_failure(mock_llm_first_bad_then_good)
def test_returns_failure_after_max_attempts(mock_llm_always_bad)
def test_extracts_source_strips_code_fences()
```

### `tests/mutation/test_mutation_store.py`

```python
def test_save_auto_approves_above_threshold()
def test_save_stages_below_threshold()
def test_write_tool_to_disk_atomic()
def test_load_tools_on_startup_restores_all_approved()
def test_rejected_tool_not_written_to_disk()
```

---

## What This Prompt Does NOT Do

- It does not wire the gap detector trigger path (Prompt 151).
- It does not implement operator approval UI (Prompt 155).
- It does not implement quality scoring (Prompt 154).
- It does not implement prompt/persona mutation (Prompt 152).
- It does not implement self-coding mutation (Prompt 153).
- The `MutationStore` built here is partial. Prompts 152-154 extend it.
