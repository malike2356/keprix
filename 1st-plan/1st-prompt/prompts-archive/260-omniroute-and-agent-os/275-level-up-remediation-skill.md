# Keprix - Prompt 275: Level-up remediation skill

**Series:** Nate Herk AIOS adoption **274-279**  
**Master reference:** `../prompts-archive/ref-273-nate-herk-aios-adoption-master-reference.md`  
**Depends on:** **274**  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**Level-up remediation skill** (Nate `/level-up` pattern): consumes **274** `MaturityAuditResult` and produces a prioritized action plan with concrete next steps, optional auto-fixes, and checklist items for **265**.

**Non-goals:**

- Auto-wiring connections without user approval
- Modifying production credentials
- Replacing human judgment on business priorities

---

## 2. Architecture

```text
POST /api/agent-os/maturity/{id}/export-to-level-up
        |
        v
level_up_service.py
  - rank gaps by leverage (from 274)
  - map gap -> action template
  - optional safe auto-fixes (create stub files)
        |
        v
LevelUpPlan { actions[], estimated_score_delta, checklist_hooks[] }
        |
        v
/level-up skill + /agent-os/maturity level-up tab
```

---

## 3. Data model

```python
@dataclass
class LevelUpAction:
    id: str
    title: str
    dimension: str          # context | connections | capabilities | cadence
    leverage: str           # high | medium | low
    kind: str               # manual | wizard | skill_invoke | auto_stub
    action_url: str | None
    skill_slug: str | None
    instructions_md: str
    completed: bool = False

@dataclass
class LevelUpPlan:
    plan_id: str
    source_audit_id: str
    actions: list[LevelUpAction]
    estimated_score_delta: float
    created_at: str
```

Persist: `{KEPRIX_HOME}/agent-os/level-up/{plan_id}.json`

---

## 4. Action templates (v1)

| Gap pattern | Action |
| --- | --- |
| Missing `about-business.md` | Wizard link **276** or auto-create stub from onboard intake |
| Tier-1 domain not wired | Open **277** connection wizard for that domain |
| No skills | Link Hub + suggest **257** session scan |
| No cadence | Link **260** promote + cron create |
| Context thin | Re-run onboard question 2 (writing samples) |

**Safe auto-fixes only:**

- Create empty `context/priorities.md` template
- Create stub `connections.md` from **277** template
- Append **265** checklist hook events (no auto-complete)

---

## 5. Skill: `level-up`

**Location:** `optional-skills/productivity/level-up/SKILL.md`

Flow:

1. Load latest maturity audit or accept `audit_id` argument
2. Generate `LevelUpPlan`
3. Walk operator through top 3 high-leverage actions
4. Mark actions complete; optionally re-run **274**

Invocation: `/level-up` or "help me level up my OS after the audit"

---

## 6. API routes

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/agent-os/level-up/generate` | `{ audit_id }` |
| GET | `/api/agent-os/level-up/{plan_id}` | Plan |
| POST | `/api/agent-os/level-up/{plan_id}/actions/{id}/complete` | Mark done |
| POST | `/api/agent-os/level-up/{plan_id}/re-audit` | Trigger **274** |

---

## 7. UI

Tab on `/agent-os/maturity` after audit: **Level up**

- Ordered action cards with CTAs
- Progress bar (actions completed / total)
- "Re-run audit" when all high-leverage done

---

## 8. Files to create

```
src/keprix/agent_os/
  level_up_service.py
  level_up_templates.py
  level_up_store.py

src/keprix/api/
  agent_os_level_up_routes.py

src/keprix/optional-skills/productivity/level-up/
  SKILL.md

frontend/src/app/(workspace)/agent-os/maturity/LevelUpPanel.tsx

docs/features/level-up-remediation.md

tests/agent_os/
  test_level_up_service.py
  test_level_up_templates.py
```

---

## 9. Acceptance criteria

- Generate plan from **274** fixture with >= 3 ranked actions.
- High-leverage gaps appear before low-leverage.
- Stub file auto-fix creates templates only under workspace `context/` or vault root (never outside).
- Completing action fires **265** hook event when mapped.
- Re-audit returns new score >= previous when stubs filled (unit test).
- Skill reads export JSON contract from **274** docs.

---

## 10. Dependencies

- **Requires:** **274** export contract
- **Links:** **276**, **277**, **260**, **265**
