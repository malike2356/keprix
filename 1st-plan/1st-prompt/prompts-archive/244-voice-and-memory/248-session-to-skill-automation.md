# keprix - Prompt: Session-to-Skill Automation Loop

## Purpose

Chase AI's video demonstrated a powerful pattern: review past sessions, find repeated tasks, propose skills. This is manual today -- the user asks Claude "go through our last 10 sessions, find repeated tasks, suggest skills."

keprix already has the pieces to automate this end-to-end:

- `improvement/run_analyzer.py` -- analyses agent runs
- `improvement/tool_gap_detector.py` -- detects missing tools
- `agent/keprix/mutation.py` -- mutation engine for self-coding
- `agent/keprix/gap_detector.py` -- gap detection
- `skills/` -- skill registry and management

This prompt connects them into a single automated loop: the agent watches what you do, spots patterns, and says "I have done this three times now. Want me to turn it into a skill you can trigger with one command?"

## What already exists (do not rebuild)

- `improvement/run_analyzer.py` -- RunAnalyzer: analyses runs, generates ImprovementProposal
- `improvement/eval_backfill.py` -- converts proposals to eval cases
- `improvement/feedback_collector.py` -- collects user feedback
- `improvement/tool_gap_detector.py` -- detects gaps in tool coverage
- `agent/keprix/mutation.py` -- mutation engine
- `agent/keprix/gap_detector.py` -- gap detection
- `agent/keprix/synthesiser.py` -- generates code from proposals
- `skills/` -- skill registry

## What to build

### 1. Session Pattern Detector

A background analyser that watches completed sessions for repeating patterns:

```python
# improvement/session_pattern_detector.py

@dataclass
class RepeatedTask:
    """A task the user has done multiple times that could become a skill."""
    description: str           # "Summarise property deal and email to investor"
    occurrence_count: int      # 3
    sessions: list[str]        # session IDs where this pattern appeared
    tools_used: list[str]      # ["web_search", "file_tools", "email"]
    estimated_tokens_per_run: int
    confidence: float          # 0.85 -- how sure the agent is this is a real pattern

class SessionPatternDetector:
    """Analyses agent session history to find repeated task patterns."""

    def __init__(self, session_db: SessionDB, agent: AIAgent):
        self.db = session_db
        self.agent = agent

    async def analyse_recent_sessions(self, count: int = 10) -> list[RepeatedTask]:
        """Analyse the last N sessions for repeated task patterns."""
        sessions = await self.db.get_recent_sessions(count)

        # Extract all user requests and agent actions
        all_tasks = []
        for session in sessions:
            tasks = await self.extract_tasks(session)
            all_tasks.extend(tasks)

        # Cluster similar tasks
        clusters = await self.cluster_tasks(all_tasks)

        # Filter to clusters with count >= 2
        repeated = [c for c in clusters if len(c.tasks) >= 2]

        # Score confidence based on similarity and frequency
        return [self.to_repeated_task(c) for c in repeated]

    async def extract_tasks(self, session: Session) -> list[Task]:
        """Extract discrete tasks from a session's messages."""
        # Analyse each user request and the agent's response pattern.
        # A "task" is: user request + sequence of tool calls + final output.
        ...
```

### 2. Skill Proposal Engine

When the pattern detector finds a repeated task, it generates a skill proposal:

```
Keprix has detected a repeated task pattern.

Task: "Summarise a property deal and email the summary to an investor"

Occurrences: 3 times in the last 7 days
  - Session #2841: "Summarise the Portsmouth 3-bed deal and email Marc"
  - Session #2912: "Summarise the Southampton flat and send to Angel Investor"
  - Session #2977: "Email the Brighton deal summary to Sarah"

Tools used: web_search, file_tools.read_file, email.send
Average tokens: 2,340 per run

Proposed skill: /send-deal-summary
  Usage: /send-deal-summary <property_address> <recipient_email>
  Does: Fetches the deal file, generates a one-page summary with key metrics
        (price, yield, BRR, comparables), and emails it as a PDF to the recipient.

Create this skill? [y/n/edit]
```

If the user says yes, the skill is created, added to the skill registry, and becomes available in the launcher and slash commands.

### 3. Auto-Skill Packaging

When the user approves a skill proposal, the agent auto-generates the skill pack:

```python
# improvement/skill_packager.py

class SkillPackager:
    """Packages a repeated task pattern into a skill pack."""

    async def package(self, task: RepeatedTask) -> SkillPack:
        """Generate a complete skill pack from a task pattern."""

        # 1. Generate skill definition
        skill_def = await self.agent.generate_skill_definition(
            task=task,
            examples=task.example_sessions,
        )

        # 2. Create the skill file
        skill_path = f"skills/{skill_def.slug}/SKILL.md"
        await self.write_skill_file(skill_path, skill_def)

        # 3. Generate scripts if needed
        if skill_def.requires_scripts:
            await self.generate_scripts(skill_def)

        # 4. Register in skill registry
        await skill_registry.register(skill_def)

        # 5. Generate test fixtures from example sessions
        await self.generate_tests(skill_def, task.example_sessions)

        # 6. Create improvement baseline
        # The first few runs become the baseline for the self-improvement loop
        await self.create_baseline(skill_def, task.sessions)

        return SkillPack(
            slug=skill_def.slug,
            path=skill_path,
            usage_count=task.occurrence_count,
            estimated_token_savings=task.estimated_tokens_per_run * 10,  # 10 future uses
        )
```

### 4. Improvement Baseline and Self-Improvement Loop

Once a skill is created, every run is logged. The improvement loop watches:

```
Skill: /send-deal-summary
  Runs: 12
  Average quality score: 4.2/5
  Average tokens: 2,140 (baseline: 2,340 -- 8.5% improvement)

Recent improvements:
  Run #8: Agent noticed investors prefer bullet points. Updated format.
  Run #10: Added comparable properties section (suggested by user feedback).
  Run #12: Reduced token usage by removing redundant web search when deal file
           already contains comp data.

Next improvement candidate:
  The agent could include a BRR calculation chart. 3 of 12 runs the user
  manually asked for this after receiving the summary. Add this? [y/n]
```

This is the loop engineering pattern from the video: the agent runs, logs its work, reviews past results, and proposes improvements.

```python
class SkillImprovementLoop:
    """Watches skill executions and proposes improvements."""

    def __init__(self, skill_registry: SkillRegistry, agent: AIAgent):
        self.registry = skill_registry
        self.agent = agent

    async def review_skill(self, skill_slug: str) -> list[ImprovementProposal]:
        """Review recent skill runs and propose improvements."""
        runs = await self.get_recent_runs(skill_slug, count=20)

        # Analyse patterns in user behaviour after skill execution
        follow_up_actions = await self.analyse_follow_ups(runs)
        # e.g., "user manually asked for BRR chart 3 times after the summary"

        # Analyse token efficiency trends
        token_trend = await self.analyse_token_efficiency(runs)

        # Check user feedback scores
        feedback_trend = await self.analyse_feedback(runs)

        # Generate proposals
        proposals = []
        for finding in follow_up_actions:
            if finding.frequency >= 3 and finding.confidence > 0.7:
                proposals.append(ImprovementProposal(
                    skill=skill_slug,
                    description=f"Add {finding.action} to the skill output",
                    evidence=f"User manually requested this {finding.frequency} times",
                ))

        return proposals
```

### 5. Weekly Skill Review Report

A scheduled report that summarises the agent's learning:

```
Weekly Skill Review -- Week 28, 2026

New skills created: 2
  - /send-deal-summary (from 3 repeated sessions)
  - /tenant-onboarding-checklist (from 4 repeated sessions)

Skills improved: 3
  - /property-search: added comparable filtering (suggested by pattern detector)
  - /invoice-generator: reduced token usage by 15%
  - /maintenance-scheduler: added contractor preference memory

Token savings this week: 18,340 (from skill reuse vs manual execution)

Skills needing review:
  - /competitor-analysis: quality scores dropping (3.8 -> 3.1). Review suggested.
  - /client-onboarding: user overrides output 60% of the time. Pattern mismatch.

Top pattern candidates (not yet skills):
  - "Summarise email thread and draft reply" (7 occurrences, 94% confidence)
  - "Research property area and produce rental estimate" (5 occurrences, 82% confidence)
```

### 6. User Controls

The user controls how aggressive the automation is:

```
Settings -> Agent -> Self-Improvement

Pattern detection:
  [x] Watch sessions for repeated task patterns
  [x] Propose skills when a pattern is detected (3+ occurrences)
  [ ] Auto-create skills without asking (advanced)

Skill improvement:
  [x] Review skill runs and propose improvements
  [ ] Auto-apply improvements (advanced)

Review schedule:
  [Weekly] -- when to send the skill review report

Minimum confidence for proposals:
  [70%] -- higher = fewer but more accurate proposals

Ignored patterns (never suggest skills for these):
  [chat, casual conversation, one-off questions, ...]
```

## Files to create

```
src/keprix/improvement/
  session_pattern_detector.py   - detect repeated task patterns in sessions
  skill_proposer.py             - generate skill proposals from patterns
  skill_packager.py             - auto-package patterns into skill packs
  skill_improvement_loop.py     - watch skill runs, propose improvements
  skill_review_reporter.py      - generate weekly skill review reports

src/keprix/improvement/
  pattern_clustering.py         - cluster similar tasks across sessions
  task_extractor.py             - extract discrete tasks from session messages

src/keprix/api/
  improvement_routes.py         - skill proposals API (list, approve, reject)
  skill_review_routes.py        - weekly review report API

frontend/src/app/(workspace)/
  skills/
    proposals/
      page.tsx                  - skill proposals dashboard (pending, approved, rejected)
    review/
      page.tsx                  - weekly skill review report

frontend/src/app/(workspace)/settings/
  agent/
    self-improvement/
      page.tsx                  - self-improvement settings

docs/
  agent/self-improvement-loop.md

tests/
  improvement/
    test_session_pattern_detector.py
    test_skill_proposer.py
    test_skill_packager.py
    test_skill_improvement_loop.py
    test_skill_review_reporter.py
```

## Acceptance criteria

- After 3 sessions where the user performs the same task pattern, the agent proposes a skill. The proposal appears in the dashboard and as a notification.
- Accepting a proposal creates a complete skill pack (SKILL.md, scripts if needed, test fixtures, baseline).
- The improvement loop reviews skill runs and proposes changes when it detects consistent user follow-up actions or quality score decline.
- The weekly skill review report shows new skills, improvements, token savings, and pattern candidates.
- Users can set minimum confidence threshold and minimum occurrence count for proposals.
- Users can add patterns to an ignore list so they are never proposed as skills.
- The pattern detector runs on session completion, not during active sessions (no performance impact).
