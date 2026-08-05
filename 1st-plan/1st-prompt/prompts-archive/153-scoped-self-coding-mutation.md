# Keprix - Prompt 153: Scoped Self-Coding Mutation

## Purpose

Enable Keprix's own coding agent to modify Keprix's source code within a governed
scope: specific allowed directories only, on a dedicated mutation branch, with an
automated test gate, and operator approval before any change reaches the running
system. After this prompt, an operator can tell Keprix "add a tool that does X"
and the coding agent will write the tool, run the tests, and present the diff for
approval - all without leaving Keprix.

This is Tier 3 mutation and the most powerful tier. The governance model is what
makes it safe. The scope restrictions and test gate are not optional or configurable
away - they are hardcoded constraints.

---

## Dependencies

| Prompt | Capability needed |
|---|---|
| 149 | `mutation_events` schema, `MutationStore` |
| 150 | `MutationStore.approve_mutation`, `rollback_mutation` patterns |
| 55 | `coding/repo_map.py`, `coding/patcher.py`, `coding/issue_runner.py`, `coding/git_workflow.py` |
| existing | `coding/lint_test_runner.py` test execution |
| existing | `review_gateway/` operator review pattern |

---

## Hardcoded Scope Allowlist

These are the ONLY paths the self-coding mutation agent may modify. They are
defined in `src/keprix/mutation/self_coding_scope.py` as a constant.
No environment variable or config can expand this list. An operator can DISABLE
self-coding mutation entirely but cannot grant access to paths outside this list.

```python
MUTATION_ALLOWED_PATHS = [
    "src/keprix/tools/",          # new tools, extensions to existing tools
    "src/keprix/skills/",         # skill YAML and supporting files
    "src/keprix/playbooks/",      # playbook YAML definitions
    "src/keprix/personas/",       # persona definitions and instructions
    "src/keprix/plugins/",        # operator-facing plugins
    "src/keprix/optional-skills/",# optional skill bundles
]

MUTATION_FORBIDDEN_PATHS = [
    "src/keprix/security/",
    "src/keprix/vault/",
    "src/keprix/auth/",
    "src/keprix/review_gateway/",
    "src/keprix/billing/",
    "src/keprix/governance/",
    "src/keprix/pack_gate/",
    "migrations/",
    "src/keprix/db/",
]
```

Any diff that touches a path outside `MUTATION_ALLOWED_PATHS` or inside
`MUTATION_FORBIDDEN_PATHS` is rejected before the operator even sees it.

---

## What to Build

### 1. `src/keprix/mutation/self_coding_scope.py`

```python
from pathlib import Path

MUTATION_ALLOWED_PATHS: list[str]    # as above
MUTATION_FORBIDDEN_PATHS: list[str]  # as above

def validate_diff_scope(diff_text: str) -> tuple[bool, list[str]]:
    """
    Parse a unified diff. Check every modified file path against the allowlist.
    Return (True, []) if all paths are allowed.
    Return (False, [list of forbidden paths]) if any path is outside the allowlist
    or inside the forbidden list.
    Never raises.
    """

def get_allowed_repo_root_relative_paths() -> list[str]:
    """Return MUTATION_ALLOWED_PATHS as a list for passing to repo_map.py as scope."""
```

### 2. `src/keprix/mutation/self_coding_harness.py`

Wraps the existing coding agent with mutation-specific governance.

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SelfCodingRequest:
    task: str                   # natural language description of what to build
    target_dir: str             # must be in MUTATION_ALLOWED_PATHS
    workspace_id: str
    requested_by: str           # "operator" | "agent"
    run_tests: bool = True
    branch_name: str | None = None  # auto-generated if None

@dataclass
class SelfCodingResult:
    success: bool
    mutation_id: str | None
    branch_name: str
    diff: str | None
    test_output: str | None
    test_passed: bool
    scope_valid: bool
    error: str | None
    files_changed: list[str]

async def run_scoped_mutation(
    request: SelfCodingRequest,
    store: MutationStore,
    repo_root: Path,
) -> SelfCodingResult:
    """
    Execute a scoped self-coding mutation task.

    Algorithm:
    1. Validate request.target_dir is in MUTATION_ALLOWED_PATHS.
    2. Create a git branch named request.branch_name or
       f"mutation/{timestamp}/{slugify(request.task[:40])}".
    3. Use coding/issue_runner.py or coding/chat_loop.py scoped to request.target_dir
       and MUTATION_ALLOWED_PATHS only (pass allowed paths to repo_map so the agent
       cannot see forbidden files).
    4. When coding agent produces a patch:
       a. Call validate_diff_scope(diff) to check no forbidden paths are touched.
       b. If scope invalid: discard diff, record failure, return error.
    5. Apply the patch to the mutation branch (not main).
    6. If request.run_tests:
       a. Run lint_test_runner against the mutation branch.
       b. Capture output.
       c. If tests fail: record failure with test_output, return without saving.
    7. Save the mutation to MutationStore:
       - tier="code"
       - trigger="operator" or "agent"
       - status="staged" (always; code mutations never auto-approve)
       - source_code=diff
       - metadata includes branch_name, files_changed, test_output
    8. Return SelfCodingResult with mutation_id and branch_name.
    """

def _make_branch_name(task: str) -> str:
    """Generate a safe git branch name from a task description."""
```

Code mutations are ALWAYS staged (never auto-approved), regardless of confidence
or threshold settings. Operator approval is mandatory for all code mutations.

### 3. Merge-on-approve logic in `MutationStore`

Extend `approve_mutation()` for tier="code":

```python
# In MutationStore.approve_mutation():
if record.tier == "code":
    branch_name = record.metadata.get("branch_name")
    if not branch_name:
        raise ValueError("Code mutation has no branch_name in metadata")
    _merge_mutation_branch(branch_name, repo_root=settings.repo_root)
    # After merge, reload tools if any new tool files were added
    if any(p.startswith("src/keprix/tools/") for p in record.metadata.get("files_changed", [])):
        generated_dir = Path(settings.mutation_generated_tools_dir).expanduser()
        registry.reload_generated_tools(generated_dir)
```

```python
def _merge_mutation_branch(branch_name: str, repo_root: Path) -> None:
    """
    Merge branch_name into the current working branch (usually main or dev).
    Use subprocess git merge --squash or git merge --no-ff depending on config.
    Raise on merge conflict (operator must resolve manually).
    """
```

Extend `rollback_mutation()` for tier="code":

```python
if record.tier == "code":
    branch_name = record.metadata.get("branch_name")
    # If already merged: git revert the merge commit
    # If not yet merged: just delete the branch
    _revert_or_delete_mutation_branch(branch_name, repo_root=settings.repo_root)
```

### 4. API additions to `mutation/routes.py`

```
POST /api/mutation/code/request             Trigger a scoped self-coding task
GET  /api/mutation/code                     List code mutations (paginated)
GET  /api/mutation/code/{id}                Get single code mutation record
GET  /api/mutation/code/{id}/diff           Return unified diff of the mutation
GET  /api/mutation/code/{id}/test-output    Return test runner output
POST /api/mutation/code/{id}/approve        Merge branch into main
POST /api/mutation/code/{id}/reject         Close branch, mark rejected
POST /api/mutation/code/{id}/rollback       Revert merged mutation
```

Request body for `POST /api/mutation/code/request`:
```json
{
  "task": "Add a tool that converts Markdown to PDF using pandoc",
  "target_dir": "src/keprix/tools/",
  "run_tests": true
}
```

Response: 202 Accepted with `{"mutation_id": "...", "branch_name": "mutation/..."}`

### 5. CLI command additions

```
keprix mutation code request --task "..." --target-dir src/keprix/tools/
keprix mutation code list [--status staged|approved|rejected]
keprix mutation code diff <id>
keprix mutation code approve <id>
keprix mutation code reject <id> --reason "..."
keprix mutation code rollback <id>
```

### 6. Configuration additions

```bash
KEPRIX_MUTATION_SELF_CODING=false         # disabled by default; operator must opt in
KEPRIX_MUTATION_BRANCH_PREFIX=mutation/
KEPRIX_MUTATION_MERGE_STRATEGY=squash     # squash | no-ff
KEPRIX_MUTATION_REPO_ROOT=.              # path to keprix repo root
KEPRIX_MUTATION_REQUIRE_TESTS=true
```

`KEPRIX_MUTATION_SELF_CODING=false` by default. Operators who understand the
implications set it to true. Document this clearly in the governance UI and docs.

---

## Acceptance Criteria

1. `validate_diff_scope()` returns `(False, ["src/keprix/security/auth.py"])` for
   a diff that modifies a file in `security/` and `(True, [])` for a diff that
   only modifies `src/keprix/tools/my_tool.py`.

2. `run_scoped_mutation()` with `target_dir="src/keprix/tools/"` and a task
   "create a tool that returns the current timestamp" creates a git branch, applies
   a diff, runs tests, and returns `SelfCodingResult(success=True, scope_valid=True)`.

3. A diff that touches `src/keprix/vault/` is rejected with `scope_valid=False`.
   The mutation is not saved. The git branch is deleted.

4. A mutation where tests fail returns `SelfCodingResult(test_passed=False)`.
   The mutation IS saved with `status="staged"` and `metadata.test_output` but
   the operator sees the test failure in the approval UI.

5. Code mutations always have `status="staged"` regardless of confidence. There
   is no auto-approve path for tier="code".

6. `approve_mutation()` for a code mutation merges the branch. Afterward
   `git log --oneline -1` on main shows the merge commit.

7. `rollback_mutation()` for a merged code mutation creates a revert commit.
   The original files are restored.

8. `POST /api/mutation/code/request` with `KEPRIX_MUTATION_SELF_CODING=false`
   returns 403 Forbidden.

9. The coding agent in scoped mode cannot read files in `src/keprix/security/`
   (repo_map is initialized with only the allowed paths).

---

## Tests

### `tests/mutation/test_self_coding_scope.py`

```python
def test_allowed_path_passes_validation()
def test_forbidden_path_fails_validation()
def test_path_outside_allowlist_fails_validation()
def test_diff_with_mixed_paths_fails()
def test_get_allowed_paths_returns_list()
```

### `tests/mutation/test_self_coding_harness.py`

```python
def test_scoped_mutation_creates_branch(mock_git, mock_coding_agent)
def test_scope_violation_aborts_and_deletes_branch(mock_git, mock_coding_agent_bad_diff)
def test_test_failure_saves_staged_with_output(mock_git, mock_coding_agent, mock_tests_fail)
def test_code_mutation_always_staged(mock_git, mock_coding_agent)
def test_self_coding_disabled_returns_error()
```

### `tests/mutation/test_code_mutation_routes.py`

```python
def test_request_returns_202_when_enabled()
def test_request_returns_403_when_disabled()
def test_diff_endpoint_returns_unified_diff()
def test_approve_merges_branch()
def test_reject_deletes_branch()
def test_rollback_reverts_merged_commit()
```

---

## What This Prompt Does NOT Do

- It does not add a conversation-based interface for requesting mutations. That is
  an operator API interaction. A future playbook can wrap the API for conversational
  use.
- It does not modify the test suite itself. Tests are fixed governance infrastructure.
- It does not handle merge conflicts automatically. A conflict means the operator
  must resolve manually - surface this clearly in the error response.
- Quality scoring and pruning of code mutations are in Prompt 154.
- The governance UI is in Prompt 155.
