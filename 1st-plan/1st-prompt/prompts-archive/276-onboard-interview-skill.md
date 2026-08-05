# Keprix - Prompt 276: Onboard interview skill

**Series:** Nate Herk AIOS adoption **274-279**  
**Master reference:** `../prompts-archive/ref-273-nate-herk-aios-adoption-master-reference.md`  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

**Onboard interview skill**: seven-question conversational scaffold that writes Nate-style day-one **context files** into workspace or vault (Nate `/onboard` pattern).

| # | Question | Output file |
| --- | --- | --- |
| 1 | Who are you, what do you sell, who is ICP? | `context/about-business.md` |
| 2 | Paste 1-2 recent writing samples (verbatim) | `context/writing-samples.md` |
| 3 | Top 2-3 priorities next 90 days | `context/priorities.md` |
| 4 | Biggest pains / bottlenecks | `context/about-me.md` (pains section) |
| 5 | Tools you use daily (seed for **277**) | `connections.md` draft section |
| 6 | What should the agent never do? | `context/guardrails.md` |
| 7 | Preferred working cadence (quarterly/sprint) | `context/cadence-preferences.md` |

Also writes `context/intake.json` (machine-readable answers) for **274** scoring.

**Non-goals:**

- Voice dictation integration (Glido, etc.)
- Claude Code-only clone repo flow
- Forced paid provider accounts

---

## 2. Already built

| Area | Location |
| --- | --- |
| TUI onboarding | **220-222** archived |
| Agent OS checklist | **265** |
| Workspace templates | **258** |
| Personal OS pack | **264** |

---

## 3. Architecture

```text
/onboard skill (7-phase interview)
        |
        v
onboard_interview_service.py
  - question flow state machine
  - persist answers per turn
  - render markdown files on complete
        |
        v
context/ + connections draft + intake.json
        |
        +--> 274 Context scorer reads files
        +--> 265 l0_onboard step auto-complete
        +--> 277 connections wizard prefill
```

---

## 4. Data model

```python
@dataclass
class OnboardSession:
    session_id: str
    workspace_id: str
    current_question: int      # 1-7
    answers: dict[str, str]    # q1..q7
    status: str                # in_progress | completed
    output_paths: dict[str, str]
    completed_at: str | None
```

Persist: `{KEPRIX_HOME}/agent-os/onboard/{session_id}.json`

---

## 5. Skill: `onboard`

**Location:** `optional-skills/productivity/onboard/SKILL.md`

Phases match questions 1-7. Skill rules:

- One question at a time; save after each answer
- Question 2: insist on verbatim paste (no editing)
- On complete: summarize + link day-2 (**277**) and day-7 (**274** audit)
- Embed **3 M's** habit copy (default shift, function breakdown, curiosity) in welcome message only; no separate product surface

Invocation: `/onboard` or "help me get onboarded into this OS"

---

## 6. API routes

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/agent-os/onboard/start` | `{ workspace_id }` |
| POST | `/api/agent-os/onboard/{id}/answer` | `{ question, text }` |
| POST | `/api/agent-os/onboard/{id}/complete` | Write files |
| GET | `/api/agent-os/onboard/{id}` | Session state |

---

## 7. UI

`/agent-os/onboard` wizard (optional; skill-first OK):

- Progress 1/7
- Textarea per question with examples
- Complete screen: links to **277** day-2, **274** day-7

First-login banner in **265** deep-links here for `l0_onboard`.

---

## 8. Template: `context/` preset (**258** amendment)

Add to **258** `knowledge_pipeline` and `client_delivery` presets:

```text
context/
  about-business.md
  about-me.md
  priorities.md
  writing-samples.md
  guardrails.md
  cadence-preferences.md
  intake.json
```

Update **258** `KEPRIX.md` generator to reference `context/` before wiki crawl.

---

## 9. Files to create

```
src/keprix/agent_os/
  onboard_interview_service.py
  onboard_templates.py
  onboard_store.py

src/keprix/api/
  agent_os_onboard_routes.py

src/keprix/optional-skills/productivity/onboard/
  SKILL.md
  templates/context/*.md.tpl

frontend/src/app/(workspace)/agent-os/onboard/page.tsx

docs/features/onboard-interview-skill.md

tests/agent_os/
  test_onboard_interview_service.py
  test_onboard_templates.py
```

---

## 10. Acceptance criteria

- Full 7-question flow writes all context files under workspace.
- `intake.json` valid JSON with all answers.
- `connections.md` draft includes tools from Q5.
- **274** Context scorer awards points when files present.
- **265** `l0_onboard` auto-completes on `onboard.completed` event.
- Resume in-progress session from question N+1.
- Tests cover file generation without LLM (template fill).

---

## 11. Dependencies

- **Amend:** **258** context preset, **264** include skill, **265** add `l0_onboard` step
- **Feeds:** **274**, **277**
