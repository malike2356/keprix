# Keprix - Prompt 274: Four C's OS maturity audit

**Series:** Nate Herk AIOS adoption **274-279**  
**Master reference:** `../prompts-archive/ref-273-nate-herk-aios-adoption-master-reference.md`  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**Four C's OS maturity audit**: scored assessment of operator AIOS readiness (Nate `/audit` pattern). Complements **256** workflow task audit; does not replace it.

| C | Max | Measures |
| --- | --- | --- |
| **Context** | 25 | `context/about-business.md`, `about-me.md`, `priorities.md`, writing samples |
| **Connections** | 25 | Tier-1 domains wired per **277** `connections.md` |
| **Capabilities** | 25 | Skills, promoted automations, headless actions |
| **Cadence** | 25 | Scheduled jobs, loop profiles, recent runs |

Output: `MaturityAuditResult` with total score, per-C breakdown, top gaps ranked by leverage, export JSON for **275**.

**Non-goals:**

- Claude Code project scan assumptions (use Keprix workspace + vault paths)
- Vanity leaderboard or public scores
- Replacing **256** workflow audit wizard

---

## 2. Already built (do not reimplement)

| Area | Location |
| --- | --- |
| Workflow audit (tasks) | **256** `agent_os/` |
| Skills registry | `skills/`, Hub |
| Cron / schedules | existing cron tooling |
| Vault / workspace | **258**, **259** stubs |

---

## 3. Architecture

```text
/four-cs-audit skill (slash + NL)
        |
        v
maturity_audit_service.py
  - scan_context_files()
  - scan_connections_matrix()  # reads 277 connections.md
  - scan_capabilities()
  - scan_cadence()
        |
        v
MaturityAuditResult
        |
        +--> GET /api/agent-os/maturity/{id}
        +--> POST export-to-level-up --> 275 queue
        |
        v
/agent-os/maturity UI
```

---

## 4. Data model

```python
@dataclass
class MaturityScore:
    dimension: str           # context | connections | capabilities | cadence
    score: float             # 0-25
    max_score: float = 25
    strengths: list[str]
    gaps: list[str]

@dataclass
class MaturityAuditResult:
    audit_id: str
    workspace_id: str | None
    total_score: float       # 0-100
    scores: list[MaturityScore]
    top_gaps: list[dict]     # { rank, leverage, title, fix_hint, prompt_ref }
    tier1_domains_missing: list[str]  # from 277
    scanned_at: str
```

Persist: `{KEPRIX_HOME}/agent-os/maturity/{audit_id}.json`

---

## 5. Scoring heuristics (v1)

**Context (25):**

- `about-business.md` exists with offer/ICP fields: +8
- `about-me.md` exists: +5
- `priorities.md` with 90-day items: +7
- Writing sample file or onboard intake (**276**): +5

**Connections (25):**

- Read `connections.md`; each tier-1 domain marked `status: live`: +3.5 (cap 25)
- Partial/wizard-only: +1.5

**Capabilities (25):**

- >= 3 installed skills: +8
- >= 1 promoted automation (**260** stub: cron or playbook): +9
- >= 1 headless-capable action (**262** stub): +8

**Cadence (25):**

- >= 1 active cron: +10
- >= 1 run in ledger last 7d (**261** stub OK): +8
- Weekly audit scheduled (doc or cron): +7

Document heuristics in skill + API; tunable via `cli-config.yaml`.

---

## 6. Skill: `four-cs-audit`

**Location:** `optional-skills/productivity/four-cs-audit/SKILL.md`

Phases:

1. Scan workspace + vault paths from `KEPRIX.md`
2. Call maturity API or run service inline
3. Present scored report with ranked gaps
4. Offer "Run level-up" -> **275**

Invocation: `/four-cs-audit` or "audit my OS maturity"

---

## 7. API routes

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/agent-os/maturity/run` | `{ workspace_id? }` |
| GET | `/api/agent-os/maturity/{id}` | Result |
| GET | `/api/agent-os/maturity` | History |
| POST | `/api/agent-os/maturity/{id}/export-to-level-up` | **275** input |

Feature flag: `agent_os.maturity_audit.enabled`

---

## 8. UI (`/agent-os/maturity`)

- Score ring 0-100
- Four quadrant cards (C scores)
- Gap list with "Fix" links (connections wizard **277**, onboard **276**)
- History table
- "Export to level-up" button

Nav: **Agent OS > OS maturity** (distinct from **256** Workflow audit)

---

## 9. CLI

```bash
keprix agent-os maturity run
keprix agent-os maturity show <audit_id>
keprix agent-os maturity list
keprix agent-os maturity export <audit_id> --to-level-up
```

---

## 10. Files to create

```
src/keprix/agent_os/
  maturity_audit_service.py
  maturity_scorers.py
  maturity_audit_store.py

src/keprix/api/
  agent_os_maturity_routes.py

src/keprix/optional-skills/productivity/four-cs-audit/
  SKILL.md

frontend/src/app/(workspace)/agent-os/maturity/page.tsx

docs/features/four-cs-maturity-audit.md

tests/agent_os/
  test_maturity_audit_service.py
  test_maturity_scorers.py
  test_agent_os_maturity_routes.py
```

Wire routes; add nav entry alongside **256** audit.

---

## 11. Acceptance criteria

- Audit on empty workspace returns low Context score with clear gaps (no fake high scores).
- Workspace with **276** context files scores Context >= 15.
- `connections.md` with 2 live tier-1 domains scores Connections accordingly.
- Total score = sum of four C scores.
- `export-to-level-up` produces JSON schema documented in **275**.
- Skill invocable via slash command in agent session.
- Tests cover each scorer module with fixtures.

---

## 12. Dependencies

- **Soft:** **276** onboard files, **277** connections.md
- **Complements:** **256** (different audit type)
- **Next:** **275** level-up consumes export
