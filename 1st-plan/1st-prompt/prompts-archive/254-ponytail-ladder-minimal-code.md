# keprix - Prompt: Ponytail Ladder -- Minimal Code Generation for Self-Coding and Mutation Engine

## Purpose

Ponytail (github.com/DietrichGebert/ponytail, MIT license) is a ruleset that forces AI coding agents to write minimal code. It uses a "ladder" -- before writing anything, the agent checks seven rungs. It stops at the first one that holds: YAGNI, reuse existing, stdlib, native platform, installed dep, one line, or only then write code.

Benchmarked results against bare Claude Code on a real FastAPI + React repo: **-54% lines of code, -20% cost, -27% time, 100% safe.** The ladder keeps all safety guards (validation, error handling, security, accessibility) while eliminating unnecessary code, dependencies, and over-engineering.

Ponytail already has a Hermes Agent install path, which means keprix inherits it immediately. This prompt makes ponytail a first-class citizen in keprix: bundled as a default skill, integrated into the self-coding agent, wired into the mutation engine's generation pipeline, and available as review/audit commands.

## What already exists (do not rebuild)

- `agent/keprix/mutation.py` -- mutation engine (auto-generates code)
- `agent/keprix/synthesiser.py` -- generates code from proposals
- `agent/keprix/gap_detector.py` -- gap detection
- `coding/` -- SWE-agent/Aider-style coding agent
- `coding/chat_loop.py` -- coding chat loop
- `skills/` -- skill registry
- `tools/skills_tool.py` -- skill loading

## What to build

### 1. Ponytail Skill Pack (bundled, default-on)

Package the ponytail ladder as a keprix skill that's enabled by default for all coding sessions:

```
skills/coding/ponytail/
  SKILL.md                     - skill definition
  rules/
    ladder.md                  - the seven-rung ladder
    review.md                  - ponytail-review skill
    audit.md                   - ponytail-audit skill
    debt.md                    - ponytail-debt skill
  scripts/
    install.sh                 - install from upstream ponytail repo
    update.sh                  - pull latest ladder rules
```

The skill is installed by default with keprix. Users can disable it per-session or globally. The ladder is injected into the system prompt before every coding turn.

### 2. Ladder Integration into System Prompt

The ladder is injected into the agent's system prompt for coding sessions:

```python
# agent/ladder.py

PONYTAIL_LADDER_PROMPT = """
## Code generation: climb the ladder

Before writing any code, stop at the first rung that holds:

1. Does this need to be built at all? (YAGNI)
2. Does it already exist in this codebase? Reuse the helper, util, or pattern
   that's already here. Don't rewrite it.
3. Does the standard library already do this? Use it.
4. Does a native platform feature cover it? Use it.
5. Does an already-installed dependency solve it? Use it.
6. Can this be one line? Make it one line.
7. Only then: write the minimum code that works.

The ladder runs after you understand the problem, not instead of it:
read the task and the code it touches, trace the real flow end to end,
then climb.

Rules:
- No abstractions that weren't explicitly requested.
- No new dependency if it can be avoided.
- No boilerplate nobody asked for.
- Deletion over addition. Boring over clever. Fewest files possible.
- Shortest working diff wins, but only once you understand the problem.
- Mark intentional simplifications with a `ponytail:` comment.
  If the shortcut has a known ceiling, the comment names it and the
  upgrade path.

Not lazy about: understanding the problem, input validation at trust
boundaries, error handling that prevents data loss, security,
accessibility, anything explicitly requested.
"""
```

### 3. Mutation Engine Ladder Gate

Every mutation (auto-generated code proposal) must clear the ladder before being presented to the user:

```python
# agent/keprix/ladder_gate.py

class LadderGate:
    """Validates mutation output against the ponytail ladder."""

    def __init__(self, agent: AIAgent):
        self.agent = agent

    async def validate(self, mutation: MutationProposal) -> LadderResult:
        """Check that the mutation climbed the ladder."""

        # 1. Does this need to exist?
        yagni_check = await self.agent.ask(
            f"Does this change actually need to exist? {mutation.description}"
        )
        if yagni_check == "no":
            return LadderResult.rejected("YAGNI: this change is unnecessary.")

        # 2. Does it already exist?
        reuse_check = await self.agent.ask(
            f"Does {mutation.description} already exist in the codebase?"
        )
        if reuse_check != "no":
            return LadderResult.revised(
                f"Already exists: {reuse_check}. Use that instead."
            )

        # 3-7: The agent should have climbed these before generating.
        # Verify the output doesn't introduce unnecessary deps, abstractions, etc.

        dep_check = self.check_new_dependencies(mutation)
        if dep_check.has_unnecessary:
            return LadderResult.revised(
                f"Unnecessary new dependency: {dep_check.detail}. "
                f"Rung 5: use an installed dependency instead."
            )

        boilerplate_check = self.check_boilerplate(mutation)
        if boilerplate_check.found:
            return LadderResult.revised(
                f"Boilerplate detected: {boilerplate_check.detail}. "
                f"Rung 6: can this be one line?"
            )

        return LadderResult.passed()
```

If the mutation fails the ladder, it's not presented to the user. The synthesiser regenerates with the ladder feedback. Max 3 retries.

### 4. Coding Agent Default Prompt

The coding agent (`coding/chat_loop.py`) injects the ladder into every coding session:

```python
# coding/agent_config.py

CODING_SYSTEM_PROMPT_EXTENSION = """
You are a coding agent inside keprix. You have access to the full codebase
and all keprix tools.

{ponytail_ladder_prompt}

When generating code:
- Always climb the ladder before writing.
- Reuse existing patterns, helpers, and utilities from this codebase.
- Prefer stdlib over dependencies.
- Prefer one line over a function.
- Only create new files when existing files cannot reasonably hold the change.
- Mark simplifications with `ponytail:` comments.
"""
```

### 5. ponytail-review and ponytail-audit as Slash Commands

Two slash commands available in every coding session:

```
/ponytail-review
  Review the current diff for over-engineering.
  Returns a delete-list: "Lines 45-78: The cache wrapper is unnecessary,
  functools.lru_cache does this. Lines 120-145: This helper already
  exists in utils.py. Lines 200-234: This can be a one-liner."
  Confidence: high/medium/low per suggestion.

/ponytail-audit
  Audit the entire repo for over-engineering, not just the diff.
  Scans for: unnecessary abstractions, duplicated utilities,
  dependencies that could be stdlib, files that could be deleted.
  Returns a prioritised list with estimated LOC savings per item.
```

### 6. Ladder Mode Levels

Like ponytail upstream, keprix supports four levels:

| Level | Behaviour |
|---|---|
| `off` | No ladder. Agent generates code normally. |
| `lite` | Ladder is injected once at session start. Agent follows loosely. |
| `full` (default) | Ladder is injected before every coding turn. Mutation engine uses the ladder gate. |
| `ultra` | Full + aggressive. Agent is instructed to delete over asking. "If in doubt, delete it." Rejections are marked with reasons. |

Switch with `/ponytail lite|full|ultra|off` or set default in settings.

### 7. ponytail-debt Ledger

A ledger that tracks deferred simplifications:

```
/ponytail-debt

Ponytail Debt Ledger (3 items):

1. [HIGH] utils/cache.py:120 -- wrapper around functools.lru_cache.
   Replace with direct @lru_cache usage. Est. savings: 35 lines.
   Deferred: 2026-07-05 (needs migration of 4 call sites)

2. [MEDIUM] components/DatePicker.tsx -- wraps <input type="date">.
   Remove component, use native input. Est. savings: 87 lines.
   Deferred: 2026-07-08 (blocked by Safari 14 support question)

3. [LOW] api/middleware/auth.py -- duplicates fastapi.security.
   Est. savings: 42 lines.
   Deferred: 2026-07-09

/pontail-debt add "Replace manual CORS headers with fastapi.middleware.cors"
/pontail-debt resolve 3
```

The ledger persists across sessions. Items can be marked `ponytail:` in code as a deferral marker. `/ponytail-debt harvest` scans the codebase for these markers and adds them to the ledger.

### 8. Ladder Effectiveness Dashboard

A dashboard widget showing the impact of the ladder:

```
Ponytail Ladder -- Last 30 Days

Code avoided:
  Lines not written:    1,847
  Files not created:    47
  Dependencies not added: 12

Savings:
  Token reduction:      -22% (est. 1.2M tokens saved)
  Cost reduction:       -20% (est. $4.80 saved)
  Time reduction:       -27% (est. 3.4 hours saved)

Review effectiveness:
  /ponytail-review runs: 23
  Suggestions accepted:  67% (31 of 46)
  Lines removed:         412

Top ladder rungs hit:
  1. YAGNI:             34%  (didn't need to exist)
  2. Already exists:    28%  (reused existing code)
  6. One line:          18%  (simplified to one-liner)
  3. Stdlib:            12%  (stdlib covered it)
  5. Installed dep:      5%  (used existing dep)
  4. Native platform:    3%  (browser/OS did it)
```

## Files to create

```
skills/coding/ponytail/
  SKILL.md                     - skill definition
  rules/
    ladder.md                  - seven-rung ladder ruleset
    review.md                  - ponytail-review skill
    audit.md                   - ponytail-audit skill
    debt.md                    - ponytail-debt skill
  scripts/
    install.sh                 - install/update from upstream

src/keprix/agent/
  ladder.py                    - ladder system prompt injection
  ladder_mode.py               - mode switching (lite/full/ultra/off)

src/keprix/agent/keprix/
  ladder_gate.py               - mutation engine ladder validation

src/keprix/coding/
  ladder_review.py             - ponytail-review: diff over-engineering scan
  ladder_audit.py              - ponytail-audit: full repo scan
  ladder_debt.py               - ponytail-debt ledger
  ladder_metrics.py            - effectiveness tracking

src/keprix/api/
  ladder_routes.py             - ladder mode, review, audit, debt API

frontend/src/app/(workspace)/
  coding/
    ladder/
      page.tsx                 - ladder effectiveness dashboard

docs/
  coding/ponytail-ladder.md

tests/
  agent/
    test_ladder.py
    test_ladder_gate.py
  coding/
    test_ladder_review.py
    test_ladder_audit.py
    test_ladder_debt.py
```

## Acceptance criteria

- The ponytail ladder is injected into the system prompt for all coding sessions by default (mode: full).
- The mutation engine validates every generated change against the ladder. Changes that fail the ladder are regenerated with feedback (max 3 retries).
- `/ponytail-review` scans the current diff and returns a prioritised delete-list with confidence scores.
- `/ponytail-audit` scans the entire repo for over-engineering and returns savings estimates.
- `/ponytail-debt` tracks deferred simplifications with a persistent ledger.
- The ladder dashboard shows LOC avoided, tokens saved, cost saved, and time saved over configurable periods.
- Users can switch ladder modes per-session (`/ponytail lite|full|ultra|off`) or set a global default.
- The ladder never removes validation, error handling, security, or accessibility code.
