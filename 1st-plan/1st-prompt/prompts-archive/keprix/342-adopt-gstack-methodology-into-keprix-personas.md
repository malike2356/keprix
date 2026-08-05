# Keprix Prompt 342: Adopt gstack; Garry Tan's Software Factory into Keprix Personas

## Status: PENDING

## Source
gstack by Garry Tan (YC CEO); https://github.com/garrytan/gstack
122K stars, MIT license. Cloned to: `competitor-research/00-agents-to-adopt/gstack/`

---

## Summary

Garry Tan hasn't written code since December 2025. He runs YC full-time and builds production software using 23 AI specialists (slash commands) + 8 power tools in Claude Code. 810× productivity, 40+ features in 60 days. This is the exact same thesis as Keprix; an Agent OS that turns one person into a full engineering team.

**The task:** Extract gstack's 23 skills, adapt them to Keprix's 11 persona system (NEXUS, FORGE, WARDEN, SAGE, BEACON, PRISM, COMPASS, EMBER, ECHO, CODEX, SCOUT), and build the equivalent slash-command architecture inside Keprix.

---

## Why This Matters

| What Garry Proved | Implication for Keprix |
|-------------------|----------------------|
| 23 specialists > 1 generalist | Keprix's 11 personas are the right architecture; we just need to give them specific slash commands |
| Sprint workflow: Think → Plan → Build → Review → Test → Ship → Reflect | This is a proven process. Build it into Keprix as a guided flow. |
| `SKILL.md` format with triggers, allowed-tools, methodology | This is the standard format for Keprix persona prompts. Adopt it. |
| gbrain memory system (context queries) | Keprix needs persistent memory across sessions. Already partially built. |
| "Preamble tier" system (1=always, 2=on-demand, 3=user-triggered) | Smart context loading. Only load what's needed. |
| Natural language triggers (voice + text) | Users should say "security audit" and WARDEN activates. |
| Cross-model second opinions | Keprix's multi-model routing can do this natively. |
| Safety guardrails: `/careful`, `/freeze`, `/guard`, `/unfreeze` | These ARE Scout commands. Wire them. |

---

## The 23 gstack Skills → Keprix Persona Mapping

```
THINK PHASE
───────────
/office-hours           → NEXUS (orchestrator); "YC Office Hours" product interrogation
/plan-ceo-review        → COMPASS (strategy); CEO-mode scope challenge (4 modes)
/plan-eng-review        → FORGE (CTO); Engineering feasibility review
/plan-design-review     → BEACON (marketing); Design + UX review
/plan-devex-review      → FORGE (CTO); Developer experience review

BUILD PHASE
───────────
/autoplan               → NEXUS (orchestrator); Run all reviews sequentially, auto-decide
/codex                  → CODEX (legal); Legal/compliance review
/design-consultation    → BEACON (marketing); Design brainstorming
/design-shotgun         → BEACON (marketing); Rapid design exploration
/design-html            → BEACON (marketing); HTML/CSS design generation

REVIEW PHASE
────────────
/review                 → FORGE (CTO); Pre-landing PR review
/design-review          → BEACON (marketing); Design quality review
/devex-review           → FORGE (CTO); DevEx quality review
/cso                    → WARDEN (CISO); Security audit + threat modeling
/investigate            → WARDEN (CISO) + SAGE; Root cause debugging

TEST PHASE
──────────
/qa                     → PRISM (SEO) + FORGE; QA testing + auto-fix bugs
/qa-only                → PRISM (SEO); QA without auto-fix
/benchmark              → SAGE (research); Performance benchmarking

SHIP PHASE
──────────
/ship                   → NEXUS (orchestrator); Merge, test, version, changelog, PR
/land-and-deploy        → NEXUS (orchestrator); Full deploy pipeline
/canary                 → NEXUS (orchestrator); Canary/gradual rollout

REFLECT PHASE
─────────────
/retro                  → SAGE (research); Weekly retrospective
/document-release       → ECHO (receptionist); Release notes generation
/document-generate      → ECHO (receptionist); Documentation generation

OPS & SAFETY
────────────
/browse                 → PRISM (SEO); Web browsing
/connect-chrome         → EMBER (coach); Chrome connection
/setup-deploy           → FORGE (CTO); Deployment setup
/setup-gbrain           → SAGE (research); Knowledge base setup
/setup-browser-cookies  → EMBER (coach); Browser auth setup
/careful                → SCOUT (governance); Raise caution level
/freeze                 → SCOUT (governance); Lock file editing
/guard                  → SCOUT (governance); Enable safety guardrails
/unfreeze               → SCOUT (governance); Release lock
/gstack-upgrade         → NEXUS (orchestrator); Self-update
/learn                  → SAGE (research); Learn from gbrain
```

---

## The gstack SKILL.md Format; Adopt for Keprix Personas

Every Keprix persona should follow this format:

```yaml
---
name: nexus-orchestrator
preamble-tier: 1              # 1=always loaded, 2=on-demand, 3=triggered
version: 1.0.0
description: YC Office Hours product interrogation. Sprint phase: THINK.
allowed-tools:                 # Tools this persona can use
  - terminal
  - read_file
  - search_files
  - web_search
  - delegate_task
  - write_file
triggers:                      # Natural language triggers (voice + text)
  - brainstorm this
  - is this worth building
  - help me think through
  - office hours
  - sprint planning
gbrain:                        # Persistent memory queries
  schema: 1
  context_queries:
    - id: prior-sessions
      kind: list
      filter:
        type: ceo-plan
      sort: updated_at_desc
      limit: 5
      render_as: "## Prior sessions in this project"
    - id: project-knowledge
      kind: filesystem
      glob: "~/.keprix/projects/{project}/*.md"
      sort: mtime_desc
      limit: 5
      render_as: "## Recent project documents"
---
```

---

## The Sprint Workflow; Build Into Keprix

```
┌─────────────────────────────────────────────────────────────┐
│                    KEPRIX SPRINT FLOW                         │
│                                                              │
│  THINK ───────→ PLAN ───────→ BUILD ───────→                 │
│  │                │              │                            │
│  │ NEXUS          │ NEXUS        │ FORGE                     │
│  │ /office-hours  │ /autoplan    │ CODEX                     │
│  │ COMPASS        │ COMPASS      │ BEACON                    │
│  │ /plan-ceo      │ FORGE        │ EMBER                     │
│  │                │ BEACON       │                            │
│  └────────────────┴──────────────┴────────────────────────── │
│                                                              │
│  REVIEW ───────→ TEST ───────→ SHIP ───────→ REFLECT        │
│  │                │              │              │             │
│  │ FORGE          │ PRISM        │ NEXUS        │ SAGE        │
│  │ /review        │ /qa          │ /ship        │ /retro      │
│  │ WARDEN         │ SAGE         │ /land-deploy │ ECHO        │
│  │ /cso           │ /benchmark   │ /canary      │ /docs       │
│  │ /investigate   │              │              │             │
│  └────────────────┴──────────────┴──────────────┴──────────── │
│                                                              │
│   SCOUT runs continuously: /careful, /freeze, /guard        │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation: Keprix Slash Commands

### NEXUS (Orchestrator); THINK + SHIP

```markdown
# /office-hours; YC Office Hours product interrogation

## Preamble
You are NEXUS, the YC partner. Your job is to interrogate product ideas
with brutal honesty. You don't validate; you challenge.

## The 6 Forcing Questions
1. **What problem are you solving?** Be specific. "Making X easier" is not an answer.
2. **Who has this problem right now?** Name actual people, not personas.
3. **How do they solve it today?** If the answer is "they don't," you're wrong.
4. **Why is now the right time?** What changed in the last 6 months?
5. **What's the simplest thing that could work?** Kill every feature except one.
6. **How do you know you're right?** What evidence, not what opinion.

## Process
1. Ask all 6 questions. Don't skip.
2. For each answer, ask "Why?" three times.
3. At the end, give one of three verdicts:
   - **GREEN:** Build it. Here's the simplest version.
   - **YELLOW:** Narrow scope first. Here's what to cut.
   - **RED:** Don't build this. Here's what to build instead.
```

```markdown
# /autoplan; Full review pipeline

## Preamble
Run all four reviews (CEO, eng, design, DX) sequentially.
Make decisions autonomously using these principles:

## The 6 Auto-Decision Principles
1. **Safety first:** If `/cso` finds HIGH or CRITICAL → BLOCK. Fix first.
2. **Simplicity wins:** Fewer files changed → auto-approve. Complex changes → flag.
3. **Tests required:** No test coverage change → flag.
4. **Breaking changes:** API/DB schema change → require manual review.
5. **Design debt:** Visual regression → flag with screenshot diff.
6. **Defaults rule:** Matching project conventions → auto-approve. Deviating → flag.

## Output
- Done:  Auto-approved: {count} items
- WARNING:  Flagged for review: {count} items
- Failed:  Blocked: {count} items
```

### FORGE (CTO); PLAN + REVIEW + BUILD

```markdown
# /review; Pre-landing PR review

## What to check (in order)
1. **Does it work?** Read the diff. Understand the change. Flag logic errors.
2. **Is it tested?** New code → new tests. Modified code → updated tests.
3. **Is it secure?** No secrets. No SQL injection. No XSS. No path traversal.
4. **Is it simple?** Could this be 50% shorter? Flag complexity.
5. **Does it follow conventions?** Matches project patterns? Flag deviations.
6. **Is it documented?** New API → docs. New flag → documented.

## Output format
```
## Review: {PR title}

### Done:  Approved
- {item}: {why it's good}

### WARNING:  Suggestions
- {item}: {what to change + why}

### Failed:  Must Fix
- {item}: {what's broken + how to fix}
```
```

### WARDEN (CISO); SECURITY

```markdown
# /cso; Chief Security Officer audit

## Two modes

### Daily (zero-noise)
- Scan for hardcoded secrets (API keys, tokens, passwords)
- Check dependency vulnerabilities (npm audit, pip audit)
- Verify no new ports exposed
- Check CSP headers unchanged
- Confidence gate: 8/10 (only flag if very confident)
- Output: "Done:  Clean" or "WARNING:  {N} issues"

### Comprehensive (monthly)
- Full OWASP Top 10 review
- STRIDE threat model on new features
- Supply chain audit (all deps, transitive)
- Secrets archaeology (full git history)
- CI/CD pipeline security
- LLM/AI security (prompt injection, data exfiltration)
- Skill supply chain scan
- Active verification (actually test exploits)
- Confidence gate: 2/10 (flag anything suspicious)
- Output: Full report with CVSS scores

## /investigate; Root cause debugging

1. **Reproduce:** Can you trigger the bug consistently?
2. **Isolate:** What's the smallest change that fixes it?
3. **Trace:** Follow the data. Where does it enter? Where does it break?
4. **Root cause:** Not "it broke because X is null." WHY is X null?
5. **Fix:** One-line fix preferred. If more, explain why.
6. **Prevent:** What test would have caught this?
```

### PRISM (SEO/QA); TEST

```markdown
# /qa; QA test + auto-fix

## Browser test
1. Navigate to {URL}
2. Test: Login, signup, main workflow, edge cases
3. For each bug found:
   a. Document: screenshot, steps to reproduce, expected vs actual
   b. Fix: if simple (CSS, typo, logic), fix it now
   c. Flag: if complex (architecture, data), flag for engineering

## API test
1. Test all endpoints: 200 on success, 4xx on bad input, 5xx on error
2. Test auth: 401 without token, 403 with wrong role
3. Test rate limits: 429 after threshold
4. Test edge cases: empty body, huge payload, special chars

## Output
-  Passed: {count}
-  Fixed: {count} (auto-fixed)
-  Flagged: {count} (needs engineering)
```

### SAGE (Research); REFLECT + BENCHMARK

```markdown
# /retro; Weekly engineering retrospective

## Questions
1. **What went well this week?** Celebrate wins. Name specific people.
2. **What went wrong?** Blameless. Focus on process, not people.
3. **What did we learn?** One thing that changed how you'll work next week.
4. **What's the one thing to improve next week?** Pick ONE. Not five.
5. **What's the risk nobody is talking about?** Surface the uncomfortable thing.

## Output
Save to ~/.keprix/retros/{date}-retro.md
Update gbrain with key learnings.
```

---

## The 8 Power Tools; Adopt for Keprix

| gstack Tool | What It Does | Keprix Equivalent |
|-------------|-------------|-------------------|
| **Cross-model 2nd opinion** | Send code to different model for review | Keprix multi-model routing; already built |
| **Safety guardrails** | `/careful`, `/freeze`, `/guard`, `/unfreeze` | Scout kill-switch, session block, tool quarantine |
| **Edit locks** | Prevent file modification during review | Scout `/freeze` → `chattr +i` via Sentinel |
| **Self-updater** | `/gstack-upgrade` | `keprix upgrade` (prompt 85) |
| **Browser-automation** | `/connect-chrome`, `/browse` | Keprix browser tools |
| **Deploy pipeline** | `/setup-deploy`, `/land-and-deploy` | Build CI/CD integration |
| **Knowledge base** | `/setup-gbrain`, `/learn` | Keprix vault (Obsidian-compatible) + WARDEN knowledge |
| **Context save/restore** | Save session state | Keprix sessions + memory |

---

## What Keprix Already Has vs What gstack Proves We Need

| Feature | Keprix Status | gstack Status | Action |
|---------|--------------|---------------|--------|
| Persona system (11 specialists) | Done:  Built | Failed:  Not a concept | We have this advantage |
| Slash commands | WARNING:  Partial (TUI only) | Done:  23 skills | Build slash-command system |
| Sprint workflow | Failed:  None | Done:  Think→Plan→Build→Review→Test→Ship→Reflect | Build guided sprint flow |
| Natural language triggers | Failed:  None | Done:  Voice + text triggers | Build trigger system |
| SKILL.md format | Failed:  None | Done:  Standardized | Adopt the format |
| gbrain (persistent memory) | WARNING:  Partial (sessions) | Done:  Full RAG system | Build gbrain equivalent |
| Preamble tiers (context efficiency) | Failed:  None | Done:  3 tiers | Build tiered prompt loading |
| Cross-model review | Done:  Multi-model routing | Done:  2nd opinions | Already have this |
| Safety guardrails | Done:  Scout | Done:  `/careful`, `/freeze`, etc. | Wire Scout to slash commands |
| Self-updater | Done:  Prompt 85 | Done:  `/gstack-upgrade` | Already have this |
| Browser automation | Done:  Browser tools | Done:  Browser skills | Already have this |

---

## Build Order (What to Implement First)

| Phase | What | Files | Time |
|-------|------|-------|------|
| **Phase 1: Core** | Adopt SKILL.md format for all 11 personas | 11 persona files | 2 days |
| **Phase 2: Triggers** | Natural language trigger system (voice + text) | `trigger_engine.py` | 1 day |
| **Phase 3: Sprint** | Guided sprint flow: Think→Plan→Build→Review→Test→Ship→Reflect | `sprint_flow.py` | 2 days |
| **Phase 4: gbrain** | Persistent memory with context queries | `gbrain.py` | 3 days |
| **Phase 5: Preamble** | Tiered context loading (1=always, 2=demand, 3=trigger) | `preamble_loader.py` | 1 day |
| **Phase 6: Wire Scout** | Map `/careful`, `/freeze`, `/guard`, `/unfreeze` to Scout | Sentinel bridge | 1 day |

---

## Files

| # | Action | File | Purpose |
|---|--------|------|---------|
| 1 | **CREATE** | `src/keprix/personas/nexus/nexus.md` | SKILL.md for NEXUS: /office-hours, /autoplan, /ship |
| 2 | **CREATE** | `src/keprix/personas/forge/forge.md` | SKILL.md for FORGE: /review, /plan-eng, /devex |
| 3 | **CREATE** | `src/keprix/personas/warden/warden.md` | SKILL.md for WARDEN: /cso, /investigate |
| 4 | **CREATE** | `src/keprix/personas/prism/prism.md` | SKILL.md for PRISM: /qa, /qa-only |
| 5 | **CREATE** | `src/keprix/personas/sage/sage.md` | SKILL.md for SAGE: /retro, /benchmark, /learn |
| 6 | **CREATE** | `src/keprix/personas/compass/compass.md` | SKILL.md for COMPASS: /plan-ceo-review |
| 7 | **CREATE** | `src/keprix/personas/beacon/beacon.md` | SKILL.md for BEACON: /design-*, /plan-design |
| 8 | **CREATE** | `src/keprix/personas/codex/codex.md` | SKILL.md for CODEX: /codex |
| 9 | **CREATE** | `src/keprix/personas/echo/echo.md` | SKILL.md for ECHO: /document-* |
| 10 | **CREATE** | `src/keprix/personas/ember/ember.md` | SKILL.md for EMBER: /connect-chrome, /setup-browser |
| 11 | **CREATE** | `src/keprix/personas/scout/scout.md` | SKILL.md for SCOUT: /careful, /freeze, /guard, /unfreeze |
| 12 | **CREATE** | `src/keprix/skills/skill_format.py` | SKILL.md parser + preamble tier loader |
| 13 | **CREATE** | `src/keprix/skills/trigger_engine.py` | Natural language → slash command routing |
| 14 | **CREATE** | `src/keprix/skills/sprint_flow.py` | Guided sprint workflow engine |
| 15 | **CREATE** | `src/keprix/memory/gbrain.py` | Persistent memory with context queries |

---

## Acceptance Criteria

- [ ] All 11 personas have SKILL.md files in gstack format
- [ ] Each persona has natural language triggers (voice + text)
- [ ] Saying "security audit" activates WARDEN's `/cso`
- [ ] Saying "ship it" triggers NEXUS's `/ship` workflow
- [ ] `/autoplan` runs CEO, eng, design, and DX reviews sequentially
- [ ] Sprint flow: Think → Plan → Build → Review → Test → Ship → Reflect
- [ ] Preamble tiers: tier-1 always loaded, tier-2 on demand, tier-3 triggered
- [ ] gbrain saves and retrieves context across sessions
- [ ] Scout commands `/careful`, `/freeze`, `/guard`, `/unfreeze` wired to Sentinel
- [ ] Cross-model review: FORGE reviews, WARDEN audits, second model confirms

---

## The Bigger Picture

Garry Tan proved that 23 specialists + a sprint workflow = 810× productivity. Keprix has 11 personas; that's already the right architecture. We don't need to copy gstack. We need to give each persona the gstack methodology: SKILL.md format, natural language triggers, preamble tiers, gbrain memory, and a guided sprint flow.

The win isn't copying gstack. The win is doing what gstack does; but with Keprix's multi-model routing, Scout governance, and 11 named personas that have character, not just function.

Garry calls his skills `/office-hours`, `/cso`, `/ship`. We call ours NEXUS, WARDEN, FORGE. Same capability, more personality. That's the Keprix advantage.
