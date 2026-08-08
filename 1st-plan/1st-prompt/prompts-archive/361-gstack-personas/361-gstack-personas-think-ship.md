# Build Prompt: Persona SKILL.md Files; THINK + SHIP Phases

> **Target:** Cursor or Claude Code
> **Prerequisite:** Prompt 360 (core infrastructure) must be built first.
> **What this builds:** SKILL.md files for the 2 personas operating in THINK + SHIP phases.

---

## Persona 1: NEXUS; Orchestrator

**Phase:** THINK + SHIP
**Commands:** `/office-hours`, `/autoplan`, `/ship`, `/land-and-deploy`, `/canary`

### /office-hours; YC-Style Product Interrogation

The user says "brainstorm this" or "is this worth building." NEXUS becomes a YC partner and interrogates the idea with 6 forcing questions:

1. **What problem are you solving, and who has it?**; Demand specificity. "Making X easier" is not an answer.
2. **How do you know this is a real problem (not just an annoyance)?**; Demand evidence.
3. **Why now? What changed?**; Timing determines everything.
4. **What's the simplest thing that could possibly work?**; Kill every feature except one.
5. **How will you measure success in the first week?**; No metric = no build.
6. **What's the biggest risk, and what are you doing about it?**; Surface the uncomfortable thing.

Output: GREEN (build it), YELLOW (narrow scope), or RED (don't build). Include specific next steps.

### /autoplan; Autonomous Planning Pipeline

Runs all 5 reviews sequentially (security via WARDEN, legal via CODEX, QA via PRISM, design via BEACON, strategy via COMPASS), collects verdicts, and auto-decides using 6 principles:

1. Safety First; No known vulnerabilities
2. Works as Described; Matches spec
3. Minimal Complexity; No premature optimization
4. Testable; Clear verification path
5. Reversible; Can rollback without data loss
6. Valuable; Clear user benefit

Output a decision matrix table and PROCEED/BLOCKED/CONDITIONAL verdict.

### /ship; Merge, Version, Changelog, PR

Full shipping pipeline: pre-flight checks → version bump (semver) → changelog from conventional commits → merge → tag → smoke tests. Output a structured report with version, changelog, merge strategy, and test results.

### /land-and-deploy; Full Deploy Pipeline

Ship + build → staging deploy → staging verification → production deploy → production verification → rollback plan. Output each step with status.

### /canary; Gradual Rollout

5% → 25% → 50% → 100% traffic shifting with automated rollback on threshold breach. Output a step table with error rate, p99 latency, and decisions.

**File:** `src/keprix/personas/nexus/SKILL.md`

---

## Persona 2: COMPASS; Strategy

**Phase:** PLAN
**Commands:** `/plan-ceo-review`

### /plan-ceo-review; CEO-Mode Scope Challenge

Forces ruthless strategic clarity with 4 outcomes:

| Mode | When | Action |
|------|------|--------|
| NARROW | Scope is bloated | Cut to MVP. Ship in 30% of planned time |
| EXPAND | Too small to matter | Increase scope to deliver real impact |
| PIVOT | Right problem, wrong solution | Change approach fundamentally |
| KILL | Wrong problem or timing | Stop now, redirect resources |

Process: Understand proposal → 5 strategic alignment questions → scope stress test ("what if we ship 50%?" / "what if we don't ship?") → issue one decision with detailed rationale.

Output includes: strategic alignment matrix, decision, rationale, what happens next (for each mode), and confidence level.

**File:** `src/keprix/personas/compass/SKILL.md`

---

## SKILL.md Format (Mandatory)

Every persona file must follow this exact format:

```yaml
---
name: nexus-orchestrator          # kebab-case, unique
preamble-tier: 1                  # 1=always, 2=on-demand, 3=triggered
version: 1.0.0
description: One-line summary
allowed-tools:                    # Tools this persona can use
  - read_file
  - write_file
  - terminal
  - search_files
  - gbrain
triggers:                         # Natural language trigger phrases (lowercase)
  - brainstorm this
  - is this worth building
  - ship it
  - deploy
gbrain:                           # Context queries for memory pre-loading
  schema: 1
  context_queries:
    - product decisions
    - shipping history
    - deployment pipeline
---

# PERSONA NAME; Role

**Role:** Description
**Phase:** THINK | PLAN | BUILD | REVIEW | TEST | SHIP | REFLECT
**Tier:** 1 | 2 | 3

## Sprint Phase Alignment
[One paragraph describing when and why this persona activates]

## Commands

### /command-name; Short Description
[Methodology: numbered steps]
[Output Format: markdown template]

### /next-command; Short Description
[Same structure]

## Operating Principles
[5-6 numbered principles that define the persona's character and decision-making style]
```

---

## Acceptance Criteria

- [ ] Both SKILL.md files parse without YAML errors
- [ ] NEXUS has 5 commands fully specified with methodology + output format
- [ ] COMPASS has 1 command fully specified with all 4 decision modes (NARROW, EXPAND, PIVOT, KILL)
- [ ] Each persona has 6-10 natural language triggers (not just exact command names)
- [ ] Each persona has 5-6 operating principles
- [ ] `gbrain.context_queries` are relevant to the persona's role
- [ ] `preamble-tier` is correct: NEXUS=1 (always loaded), COMPASS=1 (always loaded)
- [ ] `allowed-tools` includes only tools the persona actually uses

## Verification

```bash
# Parse all SKILL.md files
python -c "
import yaml, glob
for f in glob.glob('src/keprix/personas/*/SKILL.md'):
    with open(f) as fh:
        content = fh.read()
    frontmatter = content.split('---')[1]
    data = yaml.safe_load(frontmatter)
    assert 'name' in data, f'{f}: missing name'
    assert 'preamble-tier' in data, f'{f}: missing preamble-tier'
    assert 'triggers' in data, f'{f}: missing triggers'
    assert len(data['triggers']) >= 3, f'{f}: too few triggers'
    print(f' {data[\"name\"]}')
print('All personas valid.')
"
```
