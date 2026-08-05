# keprix - Prompt 28: The keprix Agent (Self-Coding / Tool Synthesis)

## Context

Read `00a-product-vision-and-agent-consolidation-map.md`. The Mutation engine is **keprix-only**;
it is not ported from any source project. Prompt 55 later adds SWE-agent-style patch trajectories
as a complementary governed path; Prompt 28 owns the gap-detect-synthesize-approve-install loop.

This prompt implements the defining feature of keprix that is present in no
other open-source agent platform: the ability to synthesise its own tools when
it cannot complete a task with what it already has.

Build it from scratch.

Output: `keprix/backend/agent/keprix/`

The CLI banner introduced in Prompt 40 refers to this feature:
```
keprix v1.0.0 - The keprix Agent
```

## What the keprix Agent Does

When the agent's task classifier determines that no existing tool or skill can
satisfy the user's request, instead of returning "I cannot do that," the agent
enters a mutation cycle:

1. Detects the gap (no suitable tool exists)
2. Synthesises a new Python tool file using its own code-writing capability
3. Synthesises a companion `.skill` YAML file
4. Runs the generated tool in a sandboxed Docker environment
5. Presents the code and sandbox results to the owner for approval
6. On approval: installs the tool live (no restart required)
7. Retries the original task with the new tool
8. On rejection: discards the tool and optionally retries with different approach

All generated tools and their full audit trail are permanently stored in the DB,
even if later deleted.

## Architecture

```
backend/agent/keprix/
  __init__.py
  gap_detector.py       - classifies whether existing tools can handle a task
  synthesiser.py        - LLM-powered tool code generator
  sandbox.py            - Docker sandbox runner for testing generated code
  static_analyser.py    - AST-based pre-sandbox security scan
  approval.py           - approval workflow (web, Telegram/Discord inline buttons, CLI)
  installer.py          - live tool/skill installer (no restart required)
  auditor.py            - writes to generated_tools table; permanent record
  retry.py              - retries original task with newly installed tool
```

## Step-by-Step Implementation

### Step 1: Gap Detector

`backend/agent/keprix/gap_detector.py`

Called from the main conversation loop BEFORE the tool dispatcher (Prompt 03),
but only when the dispatcher returns "no tool found for task."

```python
class GapDetector:
    def classify(self, task: str, available_tools: list[str]) -> GapReport:
        """
        Returns GapReport with:
          - has_gap: bool
          - gap_description: str  ("no tool can fetch live stock prices")
          - candidate_tool_name: str  ("fetch_stock_price")
          - candidate_approach: str  ("use yfinance library or a public REST API")
          - confidence: float  (0.0-1.0)
        """
```

The classifier uses the LLM with a structured prompt:
- Provide the task
- Provide the list of available tool names and descriptions
- Ask: "Can any of these tools accomplish the task? If not, what kind of tool
  would be needed and how could it be implemented?"
- Parse the JSON response into a GapReport

A gap is only declared if confidence > 0.7. Below that, the agent returns a
normal "I cannot do that" response.

### Step 2: Tool Synthesiser

`backend/agent/keprix/synthesiser.py`

When a gap is confirmed, the synthesiser generates code:

```python
class ToolSynthesiser:
    async def synthesise(self, gap: GapReport) -> SynthesisResult:
        """
        Returns SynthesisResult with:
          - tool_name: str
          - tool_code: str   (complete Python file)
          - skill_yaml: str  (companion .skill file)
          - description: str (one-line description for the registry)
          - test_input: dict (test parameters for sandbox)
        """
```

The synthesiser calls the LLM with:
- The gap description and candidate approach
- The `ToolDefinition` interface from Prompt 05 (the exact Python ABC the tool must implement)
- The tool registry format from Prompt 05
- A collection of 3 existing simple tools as concrete examples of correct implementation
- Instructions:
  - The tool must subclass `ToolDefinition`
  - It must implement `name`, `description`, `parameters_schema`, and `execute(params) -> str`
  - It may import from: stdlib, any package already in `pyproject.toml`
  - It may NOT use: `subprocess` with `shell=True`, `eval()`, `exec()`, `__import__()`,
    `os.system()`, `ctypes`, hardcoded credentials
  - Network calls are allowed but must use `httpx` (already in deps) and must respect SSRF rules
  - The tool must handle errors gracefully and return a string result

The synthesiser also generates the companion `.skill` YAML:
```yaml
name: fetch_stock_price
description: Fetches the current stock price for a given ticker symbol
triggers:
  - "stock price"
  - "what is {ticker} trading at"
  - "current price of {ticker}"
tools:
  - fetch_stock_price
```

### Step 3: Static Analyser

`backend/agent/keprix/static_analyser.py`

Runs BEFORE the sandbox. Uses Python's `ast` module to scan the generated code.
Blocks synthesis if any of the following are found in the AST:

- `subprocess.call`, `subprocess.run`, `os.system`, `os.popen` with `shell=True`
  (shell=False subprocess is allowed)
- `eval(`, `exec(`, `__import__(`, `compile(`
- `open(` with paths outside `~/.keprix/workspace/` (file writes)
- Network calls to hardcoded IPs (only hostnames allowed, no `127.0.0.1`-style bypasses)
- Imports of: `ctypes`, `cffi`, `socket` (raw sockets), `pickle`
- Any call to another tool synthesis function (blocks recursive mutation)
- Any import or reference to `backend.auth`, `backend.security`, `backend.vault`

If the static analyser blocks the code, the gap detector returns to the synthesiser
with the specific violation and asks it to rewrite. Max 2 retries on static analysis
failure before abandoning the mutation cycle.

```python
class StaticAnalyser:
    def scan(self, code: str) -> AnalysisResult:
        """
        Returns AnalysisResult with:
          - safe: bool
          - violations: list[str]  (human-readable descriptions of violations)
          - severity: str          ('block', 'warn')
        """
```

### Step 4: Sandbox Runner

`backend/agent/keprix/sandbox.py`

Runs the generated tool in an isolated Docker container:

```python
class SandboxRunner:
    async def run(self, tool_code: str, test_input: dict, timeout_s: int = 30) -> SandboxResult:
        """
        1. Write tool_code to a temp file
        2. Spin up a minimal Docker container:
           docker run --rm --network=none --memory=256m --cpus=0.5 \
             -v /tmp/carina_sandbox/:/sandbox/:ro \
             python:3.11-slim \
             python /sandbox/tool_runner.py
        3. Capture stdout/stderr
        4. Return SandboxResult with output, exit_code, duration_ms, memory_used
        """
```

Sandbox constraints (enforce via Docker flags):
- `--network=none` - NO network access in sandbox
- `--memory=256m` - memory cap
- `--cpus=0.5` - CPU cap
- `--read-only` - filesystem read-only (sandbox dir mounted separately)
- `timeout_s=30` - hard timeout; container killed after this

`tool_runner.py` (injected into sandbox):
```python
import json, sys
from generated_tool import GeneratedTool  # the synthesised class

tool = GeneratedTool()
result = tool.execute(json.loads(sys.argv[1]))
print(json.dumps({"result": result}))
```

SandboxResult:
```python
@dataclass
class SandboxResult:
    passed: bool
    output: str
    stderr: str
    exit_code: int
    duration_ms: int
    memory_mb: float
```

### Step 5: Approval Workflow

`backend/agent/keprix/approval.py`

After a successful sandbox run, the system presents the generated tool to the
owner for approval before installing it.

```sql
CREATE TABLE generated_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_that_triggered TEXT NOT NULL,    -- the original user message
    tool_name TEXT NOT NULL,
    tool_code TEXT NOT NULL,              -- full generated Python code
    skill_yaml TEXT NOT NULL,
    description TEXT NOT NULL,
    gap_description TEXT NOT NULL,
    static_analysis JSONB NOT NULL,       -- AnalysisResult
    sandbox_result JSONB NOT NULL,        -- SandboxResult
    status TEXT DEFAULT 'pending',        -- 'pending', 'approved', 'rejected', 'installed'
    approver_id TEXT,                     -- user_id of approver
    approver_channel TEXT,                -- 'web', 'telegram', 'discord', 'cli'
    rejection_reason TEXT,
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    installed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON generated_tools (status, created_at DESC);
```

Records are NEVER deleted from this table. Status transitions: pending -> approved -> installed,
or pending -> rejected. Approved tools that are later manually deleted from the filesystem
remain in the table with status 'installed'.

#### Approval Channels

**Web UI**: An approval card appears in the chat conversation:
```
The keprix Agent created a new tool to handle your request.

Tool name: fetch_stock_price
Description: Fetches current stock price using Yahoo Finance API
Sandbox: PASSED (0.4s, 12MB)

[View Code] [Approve] [Reject]
```

"View Code" opens a syntax-highlighted code drawer.
"Approve" / "Reject" call `POST /api/sdk/tools/generated/{id}/approve` or `/reject`.

**Telegram / Discord**: Inline buttons sent to the configured admin channel (not the
user's message channel, unless they are the admin):
```
NEW TOOL PENDING APPROVAL

Task: fetch AAPL stock price
Tool: fetch_stock_price
Sandbox: PASSED in 0.4s

/approve_{id} or /reject_{id}
```

**CLI**: `python -m keprix tools pending` lists tools awaiting approval.
`python -m keprix tools approve {id}` / `tools reject {id} --reason "..."`.

### Approval API Endpoints

```
GET    /api/agent/tools/generated            - list all generated tools (admin)
GET    /api/agent/tools/generated/pending    - list pending approval
GET    /api/agent/tools/generated/{id}       - get full tool record with code
POST   /api/agent/tools/generated/{id}/approve  - approve and install
POST   /api/agent/tools/generated/{id}/reject   - reject
       Body: { "reason": str? }
DELETE /api/agent/tools/generated/{id}          - soft delete from filesystem (record stays)
```

### Step 6: Live Installer

`backend/agent/keprix/installer.py`

On approval:
1. Write `tool_code` to `backend/tools/generated/{tool_name}.py`
2. Write `skill_yaml` to `backend/skills/generated/{tool_name}.skill`
3. Call `tool_dispatcher.reload()` to hot-load the new tool without restart
4. Call `skill_registry.reload()` to hot-load the new skill
5. Update `generated_tools.status = 'installed'`, `installed_at = NOW()`
6. Log to `audit_log`: event_type='tool_installed', event_data: {tool_name, approver_id}

```python
class LiveInstaller:
    async def install(self, record: GeneratedTool) -> bool:
        """
        Returns True on successful install.
        If write fails (permissions, disk), returns False and does not update DB status.
        """
```

The tool dispatcher (Prompt 03) must support hot-reload. Add `reload()` to
`backend/tools/dispatcher.py` that re-scans `backend/tools/` including `generated/`.

### Step 7: Retry

`backend/agent/keprix/retry.py`

After successful installation, the agent automatically retries the original task:

```python
class keprixRetry:
    async def retry(self, original_message: str, session_id: str) -> str:
        """
        Re-enters the agent conversation loop with the original message
        and the newly installed tool available.
        Returns the agent's response.
        """
```

The retry is transparent to the user: they see the final answer, not the tool
creation process (unless they ask). The conversation history shows the full sequence.

## Security Constraints (Summary)

These constraints are enforced at multiple layers and cannot be bypassed:

1. Static analyser (AST scan) blocks dangerous patterns before sandbox
2. Sandbox runs with `--network=none` (no outbound calls during test)
3. Installed tools run in the same process as the agent (not in sandbox) but with:
   - SSRF protection from Prompt 05 applied to all HTTP calls
   - Path confinement from Prompt 05 applied to all file access
4. Generated tools CANNOT call mutation functions (`synthesise`, `install`, `approve`)
   - Enforced by static analyser checking for imports of `backend.agent.keprix`
5. Generated tools CANNOT modify `backend/auth/`, `backend/security/`, `backend/vault/`
   - Enforced by static analyser blocking those import paths
6. Every generated tool is permanently audited in `generated_tools` table
7. Admin-only approval: only users with `role='admin'` can approve tools

## Notification on Gap Detection

When the gap detector fires, immediately notify the admin via the configured
notification channel (Telegram, Discord, or web notification):

```
The keprix Agent encountered a task it cannot handle:
"fetch AAPL stock price"

Gap: No tool exists to fetch live stock prices.
Proposed solution: fetch_stock_price using Yahoo Finance API.

Working on it... [in progress indicator]
```

Update the notification when the sandbox completes, then again when awaiting approval.

## Conversation Flow

The full flow as seen in the chat UI:

```
User:    "What is the current stock price of Apple?"

Agent:   "I don't have a tool that can fetch live stock prices. Let me create one.
          Creating tool: fetch_stock_price... [spinner]
          Sandbox test: PASSED.
          Awaiting your approval. Check the approval card above."

         [Approval Card: fetch_stock_price | Sandbox: PASSED | View Code | Approve | Reject]

User:    [clicks Approve]

Agent:   "Tool approved and installed. Retrying your request now.
          
          Apple Inc. (AAPL) is currently trading at $213.42, up 0.8% today."
```

If the user rejects:
```
Agent:   "Understood. Tool rejected. Is there another way I can help you with this?"
```

## CLI Commands

```
python -m keprix tools list              - list all tools (built-in + generated)
python -m keprix tools pending           - list pending approval
python -m keprix tools approve {id}      - approve a generated tool
python -m keprix tools reject {id}       - reject a generated tool
python -m keprix tools show {id}         - show code of a generated tool
python -m keprix tools history           - all generated tools (approved, rejected, pending)
python -m keprix tools delete {id}       - remove from filesystem (record stays in DB)
```

## Frontend Pages

Add to `frontend/src/app/(workspace)/admin/` in Prompt 21:

`/admin/tools` - Tool Manager:
- Tab: Built-in (71 tools, read-only)
- Tab: Generated (all synthesised tools with status badges)
- Tab: Pending Approval (cards with approve/reject + code view)

Pending approval cards show:
- Task that triggered it
- Tool name and description
- Sandbox result (PASSED/FAILED, duration, memory)
- Code viewer (syntax highlighted)
- Approve and Reject buttons

## Configuration

Add to `.env.example`:
```bash
# keprix Agent
keprix_keprix_ENABLED=true            # set false to disable mutation entirely
keprix_keprix_SANDBOX_TIMEOUT=30     # seconds; default 30
keprix_keprix_GAP_CONFIDENCE=0.7     # min confidence to trigger mutation
keprix_keprix_ADMIN_CHANNEL=telegram # where to send approval requests
keprix_keprix_MAX_RETRIES=2          # max static analysis + sandbox retries
```

## Acceptance Criteria

- When agent receives "fetch AAPL stock price" with no stock tool installed:
  1. Gap detector fires (has_gap=True)
  2. Synthesiser generates a `fetch_stock_price.py` tool file
  3. Static analyser passes (PASSED)
  4. Sandbox runner executes the tool and returns a result
  5. Approval card appears in the web UI
  6. `GET /api/agent/tools/generated/pending` returns the pending tool record
  7. `POST /api/agent/tools/generated/{id}/approve` returns 200
  8. `backend/tools/generated/fetch_stock_price.py` exists on disk after approval
  9. Tool dispatcher hot-reloads (no restart needed)
  10. Agent retries original task and returns a stock price
- Static analyser blocks generated code containing `eval(` (test by injecting it)
- Static analyser blocks `subprocess.run(..., shell=True)` (test by injecting it)
- Static analyser blocks import of `backend.agent.keprix` in generated tool (no recursive mutation)
- Sandbox runs with `--network=none` (verify via `docker inspect`)
- `generated_tools` table record persists after tool is rejected
- `keprix_keprix_ENABLED=false` causes gap detector to skip entirely
- `python -m keprix tools pending` lists the tool after synthesis
- `python -m keprix tools approve {id}` installs the tool and triggers retry
