# Keprix - Prompt 152: Prompt and Persona Mutation

## Purpose

Make the agent's system prompts and persona instructions evolvable. Right now
system prompts are hardcoded strings. After this prompt, they are stored in the
database per workspace and per persona. The improvement loop analyzes completed
runs and writes staged improvements back to the store. Operators can review,
approve, and rollback prompt changes. The agent loads the mutated prompt on the
next session.

This is Tier 2 mutation. It compounds: each approval replaces the old prompt as
the new baseline. Rollback restores the prior version. The prompt history is a
full audit trail.

---

## Dependencies

| Prompt | Capability needed |
|---|---|
| 149 | Mutation store schema: `mutation_events` table |
| 150 | `MutationStore` base class and `approve_mutation`, `reject_mutation`, `rollback_mutation` methods |
| existing | `improvement/prompt_improver.py` produces `PromptImprovement` proposals |
| existing | `improvement/run_analyzer.py` produces `ImprovementProposal` list |
| existing | `personas/` persona registry and persona loading |

---

## Current State

`improvement/prompt_improver.py` already produces `PromptImprovement` objects
from run analysis. The `suggested_prompt` field is a string. These objects are
currently thrown away after creation. No database. No write-back. No evolution.

Personas live in `personas/` as static YAML or Python configs. They are not
workspace-specific and cannot be modified by the improvement loop.

---

## What to Build

### 1. `src/keprix/mutation/prompt_store.py`

Database-backed system prompt management, replacing hardcoded strings.

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class SystemPromptVersion:
    id: str
    workspace_id: str
    prompt_key: str           # e.g., "default", "coding", "research", persona id
    version: int              # monotonically increasing
    content: str              # the full prompt text
    is_active: bool
    created_at: datetime
    created_by: str           # "agent" | "operator" | "mutation_improver"
    mutation_id: str | None   # link to mutation_events if agent-generated
    notes: str | None

class PromptStore:
    """
    Manage workspace-level system prompt versions.
    Each (workspace_id, prompt_key) pair has a history of versions.
    Exactly one version per key is active at a time.
    """

    def get_active_prompt(self, workspace_id: str, prompt_key: str) -> str | None:
        """
        Return the content of the active version for this key, or None if no
        database entry exists (caller should fall back to the default hardcoded prompt).
        """

    def get_active_or_default(
        self,
        workspace_id: str,
        prompt_key: str,
        default: str,
    ) -> str:
        """
        Return active prompt content, or default if none is stored.
        This is the primary call site used by the agent loop.
        """

    def stage_improvement(
        self,
        workspace_id: str,
        prompt_key: str,
        suggested_content: str,
        rationale: str,
        confidence: float,
        auto_approve_threshold: float,
    ) -> SystemPromptVersion:
        """
        Save a proposed prompt improvement as a new version with is_active=False.
        Also insert a mutation_events row with tier="prompt", status="staged"
        (or "approved" if confidence >= auto_approve_threshold).
        If auto-approved, immediately set the new version as active and
        deactivate the previous version.
        Return the new version record.
        """

    def activate_version(self, version_id: str, activated_by: str) -> SystemPromptVersion:
        """
        Set this version as active. Deactivate all other versions for the
        same (workspace_id, prompt_key). Update mutation_events status to "approved".
        """

    def rollback_to_previous(self, workspace_id: str, prompt_key: str, rolled_back_by: str) -> SystemPromptVersion | None:
        """
        Find the most recently active version before the current one.
        Activate it. Mark the current version "rolled_back".
        Insert a mutation_events row with status="rolled_back" and
        rollback_of pointing to the deactivated version's mutation_id.
        Return the restored version, or None if there is no previous version.
        """

    def get_history(self, workspace_id: str, prompt_key: str, limit: int = 20) -> list[SystemPromptVersion]:
        """Return versions for this key, newest first."""
```

Database table:

```sql
CREATE TABLE system_prompt_versions (
    id            TEXT PRIMARY KEY,
    workspace_id  TEXT NOT NULL,
    prompt_key    TEXT NOT NULL,
    version       INT NOT NULL,
    content       TEXT NOT NULL,
    is_active     BOOL NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by    TEXT NOT NULL,
    mutation_id   TEXT REFERENCES mutation_events(id),
    notes         TEXT,
    UNIQUE (workspace_id, prompt_key, version)
);
CREATE INDEX ON system_prompt_versions (workspace_id, prompt_key, is_active);
```

Add migration to `migrations/versions/016_prompt_store.py`.

### 2. Wire `prompt_improver.py` write-back

In `src/keprix/improvement/routes.py`, after `propose_prompt_improvements()`
returns a list of `PromptImprovement` objects:

```python
if settings.mutation_prompt_evolution:
    for improvement in prompt_improvements:
        prompt_store.stage_improvement(
            workspace_id=workspace_id,
            prompt_key=improvement.current_prompt_hint,
            suggested_content=improvement.suggested_prompt,
            rationale=improvement.rationale,
            confidence=_estimate_confidence(improvement),
            auto_approve_threshold=settings.mutation_auto_approve_threshold,
        )
```

`_estimate_confidence()`: map `proposal.category` to confidence:
- `user_correction` -> 0.90 (user explicitly corrected; high signal)
- `low_eval` -> 0.70 (eval degradation; medium signal)
- `repeated_failure` -> 0.80 (repeated failure; high signal)

### 3. Wire agent loop to load prompts from `PromptStore`

Locate where the agent's system prompt is constructed. This is likely in
`run_agent.py`, `cli.py`, or `agents_runtime/`. Replace the hardcoded default
with `PromptStore.get_active_or_default()`:

```python
# Before (hardcoded):
system_prompt = DEFAULT_SYSTEM_PROMPT

# After:
system_prompt = prompt_store.get_active_or_default(
    workspace_id=workspace_id,
    prompt_key=active_persona_key or "default",
    default=DEFAULT_SYSTEM_PROMPT,
)
```

Ensure the `PromptStore` instance is available at agent startup. If PostgreSQL
is unavailable, fall back to the hardcoded default (not an error condition).

### 4. Persona mutation

Personas in `personas/` are currently static. Add per-workspace persona overrides
that the improvement loop can evolve.

```python
@dataclass
class PersonaMutation:
    persona_id: str
    workspace_id: str
    field: str          # "system_prompt" | "instructions" | "name" | "description"
    before_value: str
    after_value: str

class PersonaMutationStore:
    """
    Store workspace-specific overrides for persona fields.
    On persona load, apply overrides on top of the static defaults.
    """

    def get_overrides(self, workspace_id: str, persona_id: str) -> dict:
        """Return {field: value} dict of active overrides."""

    def stage_override(
        self,
        workspace_id: str,
        persona_id: str,
        field: str,
        new_value: str,
        rationale: str,
        confidence: float,
        auto_approve_threshold: float,
    ) -> MutationRecord:
        """
        Insert mutation_events row with tier="persona".
        Auto-approve if confidence >= threshold.
        For "system_prompt" field: also call PromptStore.stage_improvement()
        with prompt_key=persona_id.
        """

    def rollback_override(
        self,
        workspace_id: str,
        persona_id: str,
        field: str,
        rolled_back_by: str,
    ) -> MutationRecord | None:
        """Restore the previous value for this field."""
```

Wire persona loading: when a persona is loaded from `personas/`, merge the static
definition with `PersonaMutationStore.get_overrides(workspace_id, persona_id)`.
The merged result is what the agent sees.

### 5. API additions to `mutation/routes.py`

```
GET  /api/mutation/prompts                   List prompt versions (paginated, filterable by key)
GET  /api/mutation/prompts/{key}/history     History for a specific prompt key
POST /api/mutation/prompts/{key}/approve     Approve a staged prompt version
POST /api/mutation/prompts/{key}/rollback    Rollback to previous version
GET  /api/mutation/personas/{id}/overrides   Current persona overrides for workspace
POST /api/mutation/personas/{id}/approve     Approve a staged persona override
POST /api/mutation/personas/{id}/rollback    Rollback a persona override
```

### 6. Prompt key naming conventions

| Agent mode | Prompt key |
|---|---|
| Default workspace agent | `default` |
| Coding agent | `coding` |
| Research agent | `research` |
| COMPASS persona | persona ID from personas/ registry |
| SAGE persona | persona ID |
| FORGE persona | persona ID |
| WARDEN persona | persona ID |
| Custom operator persona | persona ID |

The improvement loop uses `record.metadata.get("persona_id", "default")` as the
prompt key when staging improvements.

---

## Acceptance Criteria

1. After a run with category `user_correction` and `mutation_prompt_evolution=true`,
   `prompt_store.get_history(workspace_id, "default")` returns at least one staged
   or approved version newer than the hardcoded default.

2. A staged prompt improvement (confidence 0.70 below threshold 0.85) sets
   `is_active=False`. The agent loop still loads the old prompt. After
   `activate_version()`, the agent loop loads the new prompt.

3. `rollback_to_previous()` restores the version that was active before the most
   recent activation. The rolled-back version has `is_active=False`.

4. `get_active_or_default(workspace_id, "default", DEFAULT)` returns `DEFAULT`
   when no database entry exists (new deployment, no evolution yet).

5. A persona loaded with an active `system_prompt` override returns the overridden
   text. The static default is not returned.

6. `GET /api/mutation/prompts/default/history` returns a list ordered newest first
   with version numbers incrementing.

7. With `mutation_prompt_evolution=false`, `stage_improvement()` is never called.
   No database writes from the improvement loop.

---

## Tests

### `tests/mutation/test_prompt_store.py`

```python
def test_get_active_returns_none_when_empty()
def test_get_active_or_default_returns_default_when_empty()
def test_stage_auto_approves_above_threshold()
def test_stage_remains_staged_below_threshold()
def test_activate_version_deactivates_previous()
def test_rollback_restores_prior_active()
def test_get_history_newest_first()
def test_fallback_when_db_unavailable()
```

### `tests/mutation/test_persona_mutation_store.py`

```python
def test_get_overrides_empty_for_new_workspace()
def test_stage_override_auto_approves()
def test_persona_load_merges_overrides()
def test_rollback_override_restores_static_default()
```

### `tests/mutation/test_prompt_mutation_routes.py`

```python
def test_list_prompt_versions_paginated()
def test_history_for_key_returns_ordered()
def test_approve_staged_version_activates()
def test_rollback_restores_previous()
```

---

## What This Prompt Does NOT Do

- It does not modify persona YAML files on disk. Mutations are stored as database
  overrides layered on top of static definitions.
- It does not implement A/B testing of prompt versions. Only one version is active
  per key per workspace at a time.
- It does not expose prompt content to end users, only to workspace operators.
- Self-coding mutation (Prompt 153) and quality scoring (Prompt 154) build on this.
