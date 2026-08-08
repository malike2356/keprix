# Keprix - Prompt 265: Agentic OS Onboarding Checklist

**Series:** Agentic OS adoption **256-265** (capstone)  
**Master reference:** `../prompts-archive/ref-255-agentic-os-adoption-master-reference.md`  
**Depends on:** **256-264** (checklist items unlock as features ship)  
**Working directory:** `/opt/lampp/htdocs/verlox/keprix/`

---

## 1. What this prompt builds

In-app **four-level checklist** teaching Chase's Agentic OS model and tracking completion:

| Level | Label | Steps |
| --- | --- | --- |
| L1 | Skills and loops | Audit, first skill, promote automation, loop baseline |
| L2 | Memory map | Workspace template, vault, first wiki article |
| L3 | Action surface | Pin action, headless run, schedule |
| L4 | Distribution | Export client kit or invite teammate |

Route: `/agent-os/onboarding` + dismissible banner on first login when `agent_os.onboarding_completed` is false.

**Day rollout (Nate Herk, prompt 273 pack):**

| Day | Step | Prompt |
| --- | --- | --- |
| Day 1 | Onboard interview | **276** `l0_onboard` |
| Day 2 | Wire first connection | **277** `l2_connect_one` |
| Day 7 | Four C's maturity audit | **274** `l2_four_cs_audit` |

**Non-goals:** Video embed of Chase channel; link to public transcript doc only. Voice dictation (Glido). Claude Code install tutorial.

---

## 2. Progress store

```python
@dataclass
class OnboardingProgress:
    user_id: str
    steps: dict[str, bool]   # step_id -> done
    completed_at: str | None
    dismissed: bool
```

Persist per user in DB or `{KEPRIX_HOME}/users/{id}/agent-os-onboarding.json`.

Step completion detected by:

- Explicit events (audit completed, skill approved, etc.)
- Manual "Mark done" for education-only steps
- Feature hooks from **256-263**

---

## 3. Step definitions

```yaml
steps:
  - id: l0_onboard
    level: 0
    title: Complete the onboard interview (Day 1)
    action_url: /agent-os/onboard
    auto_complete: onboard.completed
    copy: Default shift - ask how AI could do 30% before manual work.

  - id: l1_audit
    level: 1
    title: Complete a workflow audit
    action_url: /agent-os/audit
    auto_complete: audit.completed

  - id: l1_first_skill
    level: 1
    title: Approve your first skill proposal
    action_url: /agent-os/skill-proposals
    auto_complete: skill_proposal.approved

  - id: l1_promote
    level: 1
    title: Promote a skill to an automation
    action_url: /agent-os/promote
    auto_complete: automation.promoted

  - id: l1_baseline
    level: 1
    title: Set a loop baseline on an automation
    action_url: /agent-os/loop-profiles
    auto_complete: loop_profile.baseline_set

  - id: l2_workspace
    level: 2
    title: Create a Knowledge Pipeline workspace
    action_url: /workspace/new
    auto_complete: workspace.created_with_template

  - id: l2_vault
    level: 2
    title: Connect your vault folder
    action_url: /settings/vault
    auto_complete: vault.configured

  - id: l2_connect_one
    level: 2
    title: Wire your first connection (Day 2)
    action_url: /agent-os/connections
    auto_complete: connections.domain_live

  - id: l2_four_cs_audit
    level: 2
    title: Run a Four C's maturity audit (Day 7)
    action_url: /agent-os/maturity
    auto_complete: maturity_audit.completed

  - id: l2_wiki
    level: 2
    title: Add your first wiki article
    action_url: /documents
    auto_complete: vault.file_in_wiki

  - id: l3_pin
    level: 3
    title: Pin an action on the board
    action_url: /agent-os
    auto_complete: action_board.pin_added

  - id: l3_headless
    level: 3
    title: Run an action headless
    action_url: /agent-os
    auto_complete: headless_run.completed

  - id: l3_schedule
    level: 3
    title: Schedule a recurring action
    action_url: /agent-os
    auto_complete: cron.created_from_skill

  - id: l4_kit
    level: 4
    title: Export a client kit OR invite a teammate
    action_url: /settings/agent-os/client-kit
    auto_complete: client_kit.exported OR user.invited
```

---

## 4. API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/agent-os/onboarding` | Progress |
| POST | `/api/agent-os/onboarding/complete-step` | Manual mark (education steps) |
| POST | `/api/agent-os/onboarding/dismiss` | Hide banner |
| POST | `/api/agent-os/onboarding/reset` | Admin reset |

Internal: `agent_os/onboarding_events.py` subscribed from other modules.

---

## 5. UI

- Progress ring per level (0-100%)
- Step cards with CTA links
- "Why this matters" collapsible (short copy from master reference)
- Link: `docs/features/agent-os-overview.md`
- Confetti-free completion message (plain text)

Banner component in workspace shell when incomplete.

---

## 6. Documentation

`docs/features/agent-os-overview.md`:

- Four levels explained
- Map to prompts 256-265
- Link to Chase transcript file (internal path)
- Link to Nate Herk transcript (`youtube-bCljOfCH8Ms-transcript-meta.md`) for 3 M's / 4 C's copy
- KNIME 233 cross-link for visual authoring

---

## 7. Files to create

```
src/keprix/agent_os/
  onboarding_progress.py
  onboarding_steps.py
  onboarding_events.py

src/keprix/api/agent_os_onboarding_routes.py

frontend/src/app/(workspace)/agent-os/onboarding/page.tsx
frontend/src/components/agent-os/OnboardingBanner.tsx

docs/features/agent-os-overview.md

tests/agent_os/
  test_onboarding_progress.py
  test_onboarding_events.py
```

---

## 8. Acceptance criteria

- New user sees banner; checklist loads with all steps pending.
- Completing **256** audit auto-checks `l1_audit` via event hook.
- Steps for not-yet-shipped features stay pending (no false complete).
- Dismiss hides banner; `/agent-os/onboarding` still accessible.
- Full completion sets `onboarding_completed` and hides banner.
- Docs page renders in mkdocs nav under Features.

---

## 9. Pack complete

When **265** ships and **256-264** archived, update master reference status table to **Shipped**.
