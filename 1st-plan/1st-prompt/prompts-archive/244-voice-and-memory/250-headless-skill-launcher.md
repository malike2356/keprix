# keprix - Prompt: Headless Skill Launcher and One-Click Actions

## Purpose

Chase AI's video showed a custom dashboard where every skill is a button. Click "Inbox Brief" and Claude runs headless, returns the output. No chat, no conversation, no typing. Just click and get the result.

keprix already has the launcher page at `/launcher` with feature cards. What's missing is the ability to run any skill as a headless, one-click action from the launcher, the sidebar, or a keyboard shortcut. This closes the gap between "I have a skill" and "I use the skill."

## What already exists (do not rebuild)

- `frontend/src/app/(workspace)/launcher/page.tsx` -- launcher with feature cards
- `frontend/src/components/shell/CommandPalette.tsx` -- Ctrl+K palette
- `frontend/src/components/shell/Sidebar.tsx` -- collapsible sidebar
- `frontend/src/lib/launcherCards.ts` -- launcher card definitions
- `skills/` -- skill registry
- `agent/skill_commands.py` -- skill execution

## What to build

### 1. Headless Skill Runner

An API endpoint and frontend hook that runs a skill headless (no chat UI, no streaming conversation) and returns the result:

```python
# api/skill_run_routes.py

@router.post("/api/skills/{skill_slug}/run")
async def run_skill_headless(
    skill_slug: str,
    params: dict | None = None,
    background: bool = False,
):
    """Run a skill headless and return the result."""
    skill = await skill_registry.get(skill_slug)
    if not skill:
        raise HTTPException(404, f"Skill '{skill_slug}' not found")

    session = await create_headless_session(skill_slug)

    # Run the skill with the agent
    result = await agent.run_skill(
        skill=skill,
        params=params,
        session=session,
    )

    return {
        "skill": skill_slug,
        "status": "completed",
        "output": result.output,
        "tokens_used": result.token_count,
        "duration_ms": result.duration_ms,
        "session_id": session.id,  # for audit trail
    }
```

Frontend hook:

```typescript
// hooks/useSkillRunner.ts

export function useSkillRunner(skillSlug: string) {
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');

  const run = async (params?: Record<string, unknown>) => {
    setStatus('running');
    const result = await api.runSkill(skillSlug, params);
    setStatus('done');
    return result;
  };

  return { run, status };
}
```

### 2. Skill Card Design for One-Click Execution

Every skill card in the launcher gets a "Run" button and an optional parameter form:

```
+-----------------------------------------+
|  /send-deal-summary                     |
|  Summarise a property deal and email    |
|  it to an investor.                     |
|                                         |
|  Last run: 2 hours ago (OK)             |
|  Avg duration: 4.2s  |  Tokens: ~2,100  |
|                                         |
|  Property address: [__________________] |
|  Recipient email:  [__________________] |
|                                         |
|  [Run]  [Schedule...]                   |
+-----------------------------------------+
```

Skills without parameters show just the run button with the last run status.

Running skills show a progress indicator:

```
+-----------------------------------------+
|  /send-deal-summary              [Stop] |
|                                         |
|  Fetching deal file...          OK      |
|  Generating summary...          Running |
|  Emailing to investor...        Pending |
+-----------------------------------------+
```

Completed skills show the result with actions:

```
+-----------------------------------------+
|  /send-deal-summary              [Done] |
|                                         |
|  Deal summary sent to marc@investor.com |
|  Tokens: 2,140  |  Duration: 3.8s       |
|                                         |
|  [View output]  [Run again]  [View session] |
+-----------------------------------------+
```

### 3. Quick-Access Skill Bar

A persistent row of favourite skills at the top of the launcher or as a configurable sidebar section:

```
Quick Actions:  [/send-deal-summary]  [/daily-brief]  [/inbox-triage]  [+ Add]
```

Each button runs the skill headless immediately (no parameter form unless the skill requires input). Hover shows last run status. Right-click shows "Run with params," "Schedule," "Edit skill," "Remove from quick bar."

### 4. Scheduled Skill Execution

Skills that can run on a schedule get a "Schedule" option in the card:

```
Schedule /daily-brief:
  [x] Every weekday at 08:00
  [ ] Every day at 08:00
  [ ] Every Monday at 09:00
  [Custom cron expression...]

  Deliver to: [Current channel] [Email] [Slack] [Notification]
```

Scheduled skills appear with a clock icon and next run time in the launcher card.

### 5. Keyboard Shortcut Triggers

Skills can be assigned keyboard shortcuts:

```
Settings -> Skills -> /send-deal-summary -> Keyboard Shortcut

Assign shortcut: [Ctrl+Shift+D]

Shortcuts are global. Press Ctrl+Shift+D from anywhere in keprix to run this skill.
```

Conflicts are detected and shown.

### 6. Launcher Card Redesign

The existing launcher page gets a new layout:

```
Launcher
========

Quick Actions (your pinned skills)
[/send-deal-summary] [/daily-brief] [/inbox-triage]

All Skills (search)
[________________________] [Sort: Recent | Alphabetical | Category]

+------------------+ +------------------+ +------------------+
| /send-deal-     | | /daily-brief     | | /inbox-triage    |
| summary         | | Morning brief    | | Triage inbox     |
|                 | | with calendar,   | | emails into      |
| [Run] [Sched]   | | tasks, weather   | | action/read/     |
|                 | | [Run] [Sched]    | | archive          |
+------------------+ +------------------+ | [Run]            |
                                          +------------------+

+------------------+ +------------------+ +------------------+
| /competitor-    | | /tenant-         | | /property-       |
| analysis        | | onboarding       | | search           |
| [...]           | | [...]            | | [...]            |
+------------------+ +------------------+ +------------------+

Built-in Tools (always available)
[New Chat] [Documents] [Calendar] [Memory] [Research] [Agent Studio] [...]
```

### 7. Output Capture and Review

Headless skill runs create a session in the background. The output is captured there:

- Click "View session" on a completed skill card to see the full agent conversation that produced the output.
- Skill runs appear in the session list with a skill icon and the skill name as the title.
- Failed runs show the error and offer "Debug this run" which opens the session with the error context.

### 8. Skill Run History

A history view showing every skill run:

```
Skills -> /send-deal-summary -> History

Runs: 47 total, 45 success, 2 failed

| Date | Status | Duration | Tokens | Recipient | Output |
|------|--------|----------|--------|-----------|--------|
| Jul 9, 14:32 | OK | 3.8s | 2,140 | marc@... | [View] |
| Jul 9, 10:15 | OK | 4.1s | 2,310 | sarah@... | [View] |
| Jul 8, 16:44 | FAIL | 2.1s | 890 | -- | [Debug] |
| Jul 8, 09:00 | OK | 3.5s | 2,050 | angel@... | [View] |
```

## Files to create

```
src/keprix/api/
  skill_run_routes.py         - POST /api/skills/{slug}/run, GET /api/skills/{slug}/runs

src/keprix/skills/
  headless_runner.py          - execute a skill in headless mode, capture output
  skill_scheduler.py          - schedule recurring skill execution
  skill_shortcut_registry.py  - keyboard shortcut assignment

frontend/src/hooks/
  useSkillRunner.ts           - headless skill execution hook

frontend/src/components/launcher/
  SkillCard.tsx               - redesigned card with Run button, params, status
  SkillQuickBar.tsx           - pinned quick-access skill buttons
  SkillProgress.tsx           - progress indicator during skill execution
  SkillResult.tsx             - completed skill output with actions
  SkillScheduleDialog.tsx     - schedule configuration dialog
  SkillHistoryTable.tsx       - run history table

frontend/src/app/(workspace)/
  launcher/
    page.tsx                  - redesigned launcher with quick bar and skill grid
  skills/
    [slug]/
      history/
        page.tsx              - skill run history page

frontend/src/components/shell/
  CommandPalette.tsx          - MODIFY: add "Run skill: ..." command type

frontend/src/app/(workspace)/settings/
  skills/
    shortcuts/
      page.tsx                - skill keyboard shortcut configuration

docs/
  skills/headless-execution.md

tests/
  skills/
    test_headless_runner.py
    test_skill_scheduler.py
    test_skill_shortcut_registry.py
  frontend/
    test_skill_card.tsx
    test_skill_launcher.tsx
```

## Acceptance criteria

- Clicking "Run" on a skill card executes the skill headless and shows progress in real time.
- The agent does not open a chat session. The skill runs, returns output, and the result is displayed on the card.
- Failed runs show a "Debug" button that opens the session with full error context.
- Skills can be pinned to the Quick Actions bar and triggered with a single click.
- Skills can be scheduled to run on a cron schedule and deliver results to a configured channel.
- Skills can be assigned keyboard shortcuts. Pressing the shortcut runs the skill immediately.
- Headless skill runs create a session in the background for audit and review.
- The skill run history page shows all past runs with status, duration, tokens, and output.
