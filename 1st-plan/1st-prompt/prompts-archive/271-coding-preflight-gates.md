# Keprix - Prompt 271: Coding preflight gates

**Series:** Chase five tools adoption **267-272**.  
**Master reference:** `../prompts-archive/ref-266-chase-five-tools-adoption-master-reference.md`  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**Coding preflight gates** inspired by Ponytail/Caveman: run **before** expensive codegen loops to cut redundant work and token spend.

Gates run at session start or before `mutation`/large patch batches:

| Gate | Check |
| --- | --- |
| `repo_index` | Tree + key files already in context? skip re-read |
| `duplicate_task` | Same task description in last N turns? warn |
| `test_exists` | Target module has tests? suggest test-first |
| `diff_budget` | Estimated patch size over threshold? require confirm |
| `provider_budget` | Usage budget near limit? switch to cheaper model profile |

Output: `PreflightReport` with `proceed | warn | block` and recommendations.

Metrics feed **261** run ledger (`tokens_saved_estimate`, `gates_triggered`).

**Non-goals:**

- Mid-conversation cache-breaking that invalidates active context (Chase warns against this)
- Hard block without override for power users
- Trust upstream Ponytail benchmarks without Keprix measurement

---

## 2. Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Usage / budgets | `/usage`, usage routes |
| Compression | context compression policy |
| Mutation engine | mutation tool |
| Run ledger (planned) | **261** |

---

## 3. Architecture

```text
coding session start / before mutation
        |
        v
preflight_service.py
  - repo_index_gate
  - duplicate_task_gate
  - test_exists_gate
  - diff_budget_gate
  - provider_budget_gate
        |
        v
PreflightReport --> UI banner + agent system note
        |
        v
261 ledger hook (tokens_saved_estimate)
```

---

## 4. Data model

```python
@dataclass
class PreflightGateResult:
    gate: str
    status: str              # pass | warn | block
    message: str
    metadata: dict

@dataclass
class PreflightReport:
    report_id: str
    session_id: str
    results: list[PreflightGateResult]
    overall: str             # proceed | warn | block
    tokens_saved_estimate: int
    created_at: str
```

Persist last report per session: `{KEPRIX_HOME}/agent-os/preflight/{session_id}.json`.

---

## 5. Configuration

```yaml
coding_preflight:
  enabled: true
  diff_budget_lines: 400
  duplicate_window_turns: 8
  provider_budget_warn_pct: 85
  allow_override: true
```

Env: `KEPRIX_CODING_PREFLIGHT=1` (default on).

---

## 6. API routes

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/coding/preflight/run` | `{ session_id, intent?, mutation_plan? }` |
| GET | `/api/coding/preflight/{session_id}` | Last report |
| POST | `/api/coding/preflight/{session_id}/override` | Operator override block |

Hook: call from mutation middleware before applying large patches.

---

## 7. UI

Coding workspace banner:

- Green: all pass
- Yellow: warnings with "Proceed anyway"
- Red: block with override (if allowed)

Settings: **Agent OS > Coding preflight** toggles per gate.

Usage page: show aggregate `tokens_saved_estimate` from preflight (stub OK until **261** full ledger).

---

## 8. CLI

```bash
keprix coding preflight run --session <id>
keprix coding preflight show --session <id>
keprix coding preflight config
```

---

## 9. Files to create

```
src/keprix/coding/
  preflight_service.py
  gates/
    repo_index.py
    duplicate_task.py
    test_exists.py
    diff_budget.py
    provider_budget.py
  preflight_store.py

src/keprix/api/
  coding_preflight_routes.py

frontend/src/components/coding/PreflightBanner.tsx

docs/features/coding-preflight-gates.md

tests/coding/
  test_preflight_service.py
  test_duplicate_task_gate.py
  test_diff_budget_gate.py
```

Integrate mutation hook in existing mutation entry point.

---

## 10. Acceptance criteria

- All five gates execute with deterministic unit tests (mock session history).
- `duplicate_task` warns when same user message repeated within window.
- `diff_budget` blocks when planned lines exceed config (override clears block).
- `provider_budget` warns when usage mock exceeds threshold.
- Preflight report persisted and returned by API.
- Ledger hook writes `tokens_saved_estimate` (file or **261** API stub documented).
- Feature flag disables gates entirely (mutation proceeds unchanged).

---

## 11. Dependencies

- **Soft:** **261** run ledger for metrics
- **Uses:** usage service, session store, mutation engine
- **Parallel:** **270** design preview unrelated
