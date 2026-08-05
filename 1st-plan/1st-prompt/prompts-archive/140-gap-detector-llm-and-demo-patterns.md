# Keprix - Prompt 140: Gap Detector LLM Classifier and Demo Patterns

## Context

Read `138-chat-mutation-e2e-wiring-outline.md`.

Complete Prompt **139** first (chat mutation bridge must exist before gap
detection improvements matter in `/chat`).

This prompt makes gap detection match real user tasks, including the marketing
terminal demo line: **"Track my time on this project"**.

Output: `src/keprix/agent/keprix/gap_detector.py`,
`src/keprix/agent/keprix/gap_classifier_prompt.py` (optional),
`tests/mutation/test_gap_detector.py`.

## Problem

`GapDetector._llm_classify` is a regex stub, not an LLM call. Only stock-price
and a few keyword patterns trigger mutation. The hero terminal demo will fail in
`/chat` after Prompt 139 unless this prompt ships.

## Step 1: Demo pattern rules (fast path)

Extend `gap_detector.py` with `_time_tracking_gap`:

```python
def _time_tracking_gap(self, task: str, tool_names: set[str]) -> bool:
    if any(n in tool_names for n in ("track_time", "time_tracker", "timesheet")):
        return False
    return bool(re.search(
        r"\b(track(?:ing)?\s+(?:my\s+)?time|time\s+track|timesheet|timer)\b",
        task.lower(),
    ))
```

When matched, return:

```python
GapReport(
    has_gap=True,
    gap_description="No tool exists to track time on projects.",
    candidate_tool_name="track_time",
    candidate_approach="Store time entries with project label, start/stop or duration input.",
    confidence=0.88,
    task=task,
)
```

Add similar high-confidence patterns only when they support documented demos;
do not grow an unmaintainable regex list. The LLM path below is the long-term
source of truth.

## Step 2: Real LLM gap classifier

Replace the body of `_llm_classify` with an async LLM call when regex fast-path
does not match.

Add:

```python
async def classify_async(self, task: str, available_tools: list[str]) -> GapReport:
```

Sync `classify()` may call `asyncio.run` only in CLI contexts; the chat bridge
and agent loop must call `classify_async` directly.

### Structured prompt

Create `gap_classifier_prompt.py` with a template:

- User task (verbatim)
- Tool manifest: list of `{ name, description }` for up to 40 tools (truncate with
  "... and N more" if needed)
- Ask for JSON only:

```json
{
  "has_gap": true,
  "gap_description": "string",
  "candidate_tool_name": "snake_case",
  "candidate_approach": "string",
  "confidence": 0.0
}
```

Use `async_call_llm` from the existing LLM helper used by `ToolSynthesiser`.
Parse JSON strictly; on parse failure return `has_gap=False, confidence=0.0`.

### Confidence gate

Only return `has_gap=True` when `confidence >= get_mutation_config().gap_confidence`
(default 0.7).

### Tool descriptions

Pull descriptions from registry entries when available (`registry.get_entry(name)`);
fallback to name only.

## Step 3: Update callers

Update these call sites to use `classify_async`:

1. `chat_mutation_bridge.py` (Prompt 139)
2. `MutationEngine.detect_gap` / `run_cycle` entry if still sync
3. `POST /api/agent/tools/generated/cycle` route

Keep sync `classify()` for CLI/tests by delegating to regex fast-paths only, or
document that CLI uses async wrapper.

## Step 4: Synthesiser alignment

When `candidate_tool_name` is `track_time`, the synthesiser prompt (Prompt 28)
must produce a tool that:

- Accepts `project` (str) and `minutes` or `action` (start/stop)
- Returns JSON `{"success": true, ...}`
- Passes static analyser (no `eval`, no shell=True, no mutation imports)

Add one fixture-based test that mocks LLM synthesis output for `track_time` and
verifies static analyser accepts it.

## Step 5: Tests

Extend or create `tests/mutation/test_gap_detector.py`:

| Case | Expected |
| --- | --- |
| "Track my time on this project" + no track_time tool | `has_gap=True`, name `track_time` |
| Same + `track_time` installed | `has_gap=False` |
| "What is 2+2?" | `has_gap=False` |
| Mock LLM returns gap JSON confidence 0.85 | `has_gap=True` |
| Mock LLM returns confidence 0.5 | `has_gap=False` |
| `KEPRIX_MUTATION_ENABLED=false` | `has_gap=False` immediately |

Mock LLM in tests; do not require live API keys in CI.

## Acceptance Criteria

- `/chat` message "Track my time on this project" triggers mutation bridge (with
  Prompt 139) when no time tool exists
- LLM classifier runs for non-regex tasks when mutation enabled
- Regex fast-paths remain for stock price (Prompt 28 AC still pass)
- `pytest tests/mutation/test_gap_detector.py` passes
- No stub `pass` in `_llm_classify` production path

## Archive Checklist

Move to `prompts-archive/` and update audit + completed README.
