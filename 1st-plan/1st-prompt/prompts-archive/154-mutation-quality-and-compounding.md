# Keprix - Prompt 154: Mutation Quality and Compounding

## Purpose

Give every mutation a quality score that updates in real time as the mutation is
used in production. Prune mutations that accumulate low scores or go unused.
Track per-deployment divergence from the base Keprix install as a metric that
grows over time. After this prompt, Keprix deployments that have been running
for months have a measurable, quantified accumulated adaptation that is specific
to their operator's use patterns - the compounding effect that makes migration
costly and Keprix stickier the longer it runs.

This is Tier 4 mutation. It does not add new mutation capabilities. It makes the
existing three tiers compound.

---

## Dependencies

| Prompt | Capability needed |
|---|---|
| 150 | `MutationStore`, `mutation_events` table, `mutation_quality_samples` table |
| 151 | Tool mutations saving and hot-loading |
| 152 | Prompt and persona mutation store |
| 153 | Code mutation store and branch model |
| existing | `improvement/run_analyzer.py` run outcome analysis |
| existing | `improvement/monitoring.py` metrics |

---

## What to Build

### 1. `src/keprix/mutation/quality.py`

Score mutations based on observed outcomes each time they are used.

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class QualitySample:
    mutation_id: str
    task_id: str | None
    run_id: str | None
    outcome: str          # "success" | "failure" | "partial"
    score: float          # 1.0 = perfect, 0.0 = total failure
    feedback: str | None  # from user correction or eval result
    sampled_at: datetime

class QualityScorer:
    """
    Update quality scores for mutations after each run that used them.
    Quality score is a weighted exponential moving average:
      new_score = alpha * sample_score + (1 - alpha) * old_score
      alpha = 0.3 (recent observations weighted more heavily)
    """

    ALPHA = 0.3
    AUTO_QUARANTINE_THRESHOLD = 0.3   # score below this triggers quarantine
    AUTO_PROMOTE_THRESHOLD = 0.85     # score above this for N uses triggers promotion
    AUTO_PROMOTE_MIN_USES = 5         # minimum uses before auto-promotion

    def record_sample(
        self,
        mutation_id: str,
        outcome: str,
        run_id: str | None = None,
        task_id: str | None = None,
        feedback: str | None = None,
    ) -> float:
        """
        Insert a row into mutation_quality_samples.
        Compute new score using EMA.
        Update mutation_events.quality_score and last_used_at.
        Increment use_count.
        Check auto-quarantine and auto-promote thresholds.
        Return the new quality score.
        """

    def record_tool_use(
        self,
        tool_name: str,
        run_id: str,
        success: bool,
        error: str | None = None,
    ) -> None:
        """
        Find the mutation_events row for tool_name (tier="tool", status="approved").
        If found, call record_sample with outcome="success" or "failure".
        If not found (built-in tool): no-op.
        """

    def record_prompt_use(
        self,
        workspace_id: str,
        prompt_key: str,
        run_id: str,
        outcome: str,  # from run analyzer
    ) -> None:
        """
        Find the active mutation_events row for this prompt key.
        Call record_sample.
        """

    def _check_auto_quarantine(self, mutation_id: str, score: float) -> None:
        """
        If score < AUTO_QUARANTINE_THRESHOLD:
          - For tier="tool": deregister from registry, delete .py file,
            set status="quarantined" in mutation_events.
          - For tier="prompt": revert to previous version in prompt_store.
          - For tier="code": set status="quarantined" (already merged; flag for review).
        Send an operator notification via the notification system.
        """

    def _check_auto_promote(self, mutation_id: str, score: float, use_count: int) -> None:
        """
        If score > AUTO_PROMOTE_THRESHOLD and use_count >= AUTO_PROMOTE_MIN_USES:
          Set a "promoted" flag in metadata. Promoted mutations are visually
          distinguished in the governance UI and are given lower prune priority.
        """

    def get_quality_history(
        self,
        mutation_id: str,
        limit: int = 50,
    ) -> list[QualitySample]:
        """Return quality samples for a mutation, newest first."""
```

### 2. Wire `record_tool_use` into tool dispatch

In `tools/managed_tool_gateway.py` or wherever tool results are processed:

```python
# After a generated tool call completes:
if entry.toolset == "generated" and quality_scorer:
    quality_scorer.record_tool_use(
        tool_name=tool_name,
        run_id=current_run_id,
        success=not result.get("error"),
        error=result.get("error"),
    )
```

### 3. Wire `record_prompt_use` into run completion

In `improvement/routes.py` after run analysis:

```python
if settings.mutation_prompt_evolution and quality_scorer:
    quality_scorer.record_prompt_use(
        workspace_id=workspace_id,
        prompt_key=record.metadata.get("persona_id", "default"),
        run_id=record.run_id,
        outcome=_classify_run_outcome(record, proposals),
    )
```

`_classify_run_outcome()`: returns "success" if no failure proposals,
"partial" if some failures, "failure" if majority proposals are failures.

### 4. `src/keprix/mutation/pruner.py`

Prune low-value mutations to prevent the mutation store from degrading over time.

```python
from dataclasses import dataclass

@dataclass
class PruneReport:
    pruned_tools: list[str]
    pruned_prompts: list[str]
    pruned_code: list[str]
    total_pruned: int
    space_reclaimed_bytes: int

class MutationPruner:
    """
    Run periodically (default: daily, configurable via cron settings) to prune:
    1. Generated tools not used in KEPRIX_MUTATION_PRUNE_AFTER_DAYS days
       AND with quality_score < 0.5 (or quality_score IS NULL).
    2. Staged mutations older than 30 days that were never approved.
    3. Rolled-back mutations older than 90 days (keep for audit but delete source_code blob).
    4. Excess generated tools when total count exceeds KEPRIX_MUTATION_MAX_GENERATED_TOOLS:
       prune lowest-score tools first until under the limit.
    """

    def prune_unused_tools(self, dry_run: bool = False) -> list[str]:
        """
        Find approved tool mutations where:
          last_used_at < NOW() - prune_after_days
          AND quality_score < 0.5 (or null)
        Deregister from registry, delete .py file, set status="pruned".
        Return list of pruned tool names.
        """

    def prune_stale_staged(self, dry_run: bool = False) -> list[str]:
        """
        Find staged mutations older than 30 days.
        Set status="expired". For tool mutations: no disk file to clean up
        (staged tools are never written to disk). Return mutation ids.
        """

    def prune_excess_tools(self, dry_run: bool = False) -> list[str]:
        """
        If count(approved tool mutations) > KEPRIX_MUTATION_MAX_GENERATED_TOOLS:
        sort by quality_score ASC, use_count ASC.
        Prune lowest-ranked until under limit.
        """

    def run_full_prune(self, dry_run: bool = False) -> PruneReport:
        """
        Run all prune operations. Log results. Return PruneReport.
        In dry_run mode: compute what would be pruned but do not execute.
        """
```

Register a cron job in `cron/` to run `MutationPruner.run_full_prune()` daily.

### 5. `src/keprix/mutation/compounding.py`

Track and report deployment-specific divergence from the base Keprix install.

```python
from dataclasses import dataclass

@dataclass
class CompoundingMetrics:
    workspace_id: str
    total_mutations: int              # all time
    active_mutations: int             # currently approved/promoted
    promoted_mutations: int           # score > 0.85, uses >= 5
    avg_quality_score: float
    total_tool_uses_by_generated: int # total uses of generated tools
    mutation_age_days: float          # average age of active mutations
    divergence_score: float           # composite score 0.0 - 1.0
    tools_contributed: int            # unique generated tools still active
    prompts_evolved: int              # prompt keys with at least one evolution
    code_mutations_merged: int

def compute_compounding_metrics(workspace_id: str) -> CompoundingMetrics:
    """
    Query mutation_events and mutation_quality_samples to compute the metrics above.

    divergence_score formula:
      weighted_sum(
        tools_contributed * 0.35,
        prompts_evolved * 0.25,
        code_mutations_merged * 0.25,
        promoted_mutations * 0.15,
      ) / normalization_factor
    Clamped to [0.0, 1.0]. A deployment with no mutations has score 0.0.
    A mature deployment with 50+ tools, evolved prompts, and merged code mutations
    approaches 1.0.
    """
```

The `divergence_score` is displayed on the mutation governance dashboard and
the admin overview page. It is the operator-visible signal of how much this
deployment has adapted beyond the base Keprix install.

### 6. API additions to `mutation/routes.py`

```
GET  /api/mutation/quality/{id}           Quality history for a mutation
GET  /api/mutation/compounding            CompoundingMetrics for the workspace
POST /api/mutation/prune                  Trigger a prune run (admin only)
POST /api/mutation/prune/dry-run          Preview what would be pruned (admin only)
```

### 7. Admin overview integration

Add a "Mutation Divergence" stat card to the admin dashboard overview
(`/dashboard`). Display `divergence_score` as a percentage (0-100%) with a
label explaining what it means. Add a sparkline of `active_mutations` count
over the last 30 days.

---

## Acceptance Criteria

1. After 10 successful uses of a generated tool, `quality_score` reflects the
   EMA of 10 success samples (score 1.0 each -> quality_score approaches 1.0).

2. After 5 consecutive failures of a generated tool, `quality_score` drops below
   `AUTO_QUARANTINE_THRESHOLD` (0.3), the tool is automatically deregistered,
   the `.py` file is deleted, and an operator notification is sent.

3. A generated tool not used for `KEPRIX_MUTATION_PRUNE_AFTER_DAYS` days with
   `quality_score < 0.5` is pruned by `run_full_prune()`.

4. A generated tool with `quality_score > 0.85` and `use_count >= 5` has
   `metadata.promoted = true`.

5. `compute_compounding_metrics()` for a workspace with 5 promoted tools and 2
   evolved prompts returns `divergence_score > 0.0` and `active_mutations >= 5`.

6. `run_full_prune(dry_run=True)` returns a `PruneReport` without modifying the
   database or filesystem.

7. `POST /api/mutation/prune` requires admin role. Returns 200 with `PruneReport`.

8. The admin dashboard overview page renders a "Mutation Divergence" stat card
   showing the percentage value.

---

## Tests

### `tests/mutation/test_quality_scorer.py`

```python
def test_ema_converges_on_repeated_success()
def test_ema_drops_on_repeated_failure()
def test_auto_quarantine_below_threshold(mock_registry)
def test_auto_promote_above_threshold_after_min_uses()
def test_record_tool_use_no_op_for_builtin_tool()
def test_quality_history_newest_first()
```

### `tests/mutation/test_pruner.py`

```python
def test_prunes_unused_low_score_tool()
def test_does_not_prune_high_score_tool()
def test_prunes_stale_staged_mutation()
def test_prune_excess_removes_lowest_score_first()
def test_dry_run_does_not_modify()
def test_full_prune_returns_report()
```

### `tests/mutation/test_compounding.py`

```python
def test_zero_divergence_for_new_workspace()
def test_divergence_increases_with_tools()
def test_divergence_increases_with_evolved_prompts()
def test_divergence_increases_with_merged_code()
```

---

## What This Prompt Does NOT Do

- It does not implement the governance UI (Prompt 155).
- The divergence score is a single number, not a detailed breakdown chart - that
  is in the governance UI.
- It does not implement mutation export or portability (exporting a deployment's
  accumulated mutations to share or migrate). That is a future concern.
