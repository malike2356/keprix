# Keprix - Prompt 261: Playbook Run Ledger and Loop Profiles

**Series:** Agentic OS adoption **256-265**  
**Master reference:** `../prompts-archive/ref-255-agentic-os-adoption-master-reference.md`  
**Depends on:** **257**, playbook runtime 207-211  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**Run ledger** for playbooks, promoted skills, and Agent Apps: every execution logs inputs, outputs, eval score, tokens, duration. **Loop profiles** compare runs to baseline and propose prompt/skill tweaks (Chase loop engineering for automations, not only chat skills).

**Non-goals:** Auto-mutate playbooks without approval; full MLOps training stack.

---

## 2. Already built

| Area | Location |
| --- | --- |
| Playbook run events | `playbook/run_routes.py`, timeline UI |
| Improvement | `improvement/run_analyzer.py` |
| Evals | `evals/`, baselines |
| Scout bridge (planned) | **236** |

---

## 3. Data model

```python
@dataclass
class RunLedgerEntry:
    entry_id: str
    source_type: str       # playbook | skill | agent_app | cron
    source_id: str
    run_id: str
    workspace_id: str
    status: str
    input_summary: dict
    output_summary: dict
    eval_score: float | None
    tokens: int
    duration_ms: int
    user_corrections: list[str]
    created_at: str

@dataclass
class LoopProfile:
    source_type: str
    source_id: str
    baseline_entry_ids: list[str]
    improvement_proposals: list[dict]
```

Persist: PostgreSQL table `agent_os_run_ledger` + JSON export to workspace `runs/` folder (**258**).

---

## 4. Hooks

Register ledger writer on:

- `playbook` run complete
- Headless skill run complete (**262**)
- Agent App run complete
- Cron session complete (when skill-backed)

---

## 5. Loop profile engine

```python
class LoopProfileEngine:
    def record_baseline(self, source_type, source_id, entry_ids): ...
    def analyze_drift(self, source_type, source_id) -> list[ImprovementProposal]: ...
```

Drift signals:

- Eval score drop vs baseline
- Rising token usage
- Repeated `user_corrections` in **257** style
- Approval backlog on playbook steps

Proposals surface in `/agent-os/loop-profiles` and feed **257** improvement UI.

Emit Scout events when **236** configured (`loop.proposal.created`, `run.completed`).

---

## 6. API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/agent-os/ledger` | Filter by source |
| GET | `/api/agent-os/ledger/{entry_id}` | Detail |
| POST | `/api/agent-os/loop-profiles/{source}/baseline` | Set baseline from last N runs |
| GET | `/api/agent-os/loop-profiles/{source}/proposals` | Drift proposals |
| POST | `/api/agent-os/loop-profiles/proposals/{id}/apply` | Apply to skill/playbook (creates draft) |

---

## 7. UI

- `/agent-os/runs` table with filters
- Playbook run page: link "View in ledger"
- Loop profile card on playbook/skill detail: baseline, trend sparkline, open proposals

---

## 8. Files to create

```
src/keprix/agent_os/
  run_ledger.py
  run_ledger_store.py
  loop_profile_engine.py
  hooks.py                    # register on run complete

database/migrations/
  XXXX_agent_os_run_ledger.sql

src/keprix/api/agent_os_ledger_routes.py

frontend/src/app/(workspace)/agent-os/
  runs/page.tsx
  loop-profiles/page.tsx

docs/features/agent-os-run-ledger.md

tests/agent_os/
  test_run_ledger.py
  test_loop_profile_engine.py
```

---

## 9. Acceptance criteria

- Completing a playbook run creates ledger row with real token/duration from runtime.
- Baseline capture uses last N successful runs; drift proposal generated when eval drops >10% in tests.
- Workspace `runs/` JSON export created when workspace linked (**258**).
- Apply proposal creates editable draft playbook YAML or skill patch, not silent overwrite.
- Scout webhook fires when **236** env configured (integration test with mock server).

---

## 10. Dependencies

- **262** headless runs must call ledger hooks
- **236** optional Scout emission
