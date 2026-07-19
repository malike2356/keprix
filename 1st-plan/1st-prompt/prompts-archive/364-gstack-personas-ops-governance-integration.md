# Build Prompt: Persona SKILL.md Files; OPS + GOVERNANCE Phases + Final Integration

> **Target:** Cursor or Claude Code
> **Prerequisite:** Prompts 360-363 must be built first.
> **What this builds:** SKILL.md files for ECHO (Receptionist), EMBER (Coach), and SCOUT (Governance). Plus the final integration test that verifies all 11 personas + 5 infrastructure modules work together.

---

## Persona 9: ECHO; Receptionist

**Phase:** REFLECT
**Commands:** `/document-release`, `/document-generate`

### /document-release; Release Notes

Generate release notes from git log since last tag. Group by type (feat, fix, chore, breaking). Auto-detect version bump. Include migration guide for breaking changes. Output in a format ready for GitHub Releases, changelog.md, or customer email.

Methodology:
1. `git log {last_tag}..HEAD --oneline` → parse conventional commits
2. Group into:  Features, BUG:  Fixes,  Maintenance, WARNING:  Breaking Changes
3. Generate human-readable descriptions from commit messages
4. Write to `CHANGELOG.md` (prepend to top) and `RELEASE_NOTES.md` (standalone)

### /document-generate; Documentation

Generate documentation for a codebase, API, or feature. Output as markdown files.

Methodology:
1. Scan the target directory/module for public APIs, classes, functions
2. Extract docstrings and type hints
3. Generate: README, API reference, quickstart guide, architecture overview
4. Write to `docs/` directory

**Operating principles:** Write for the person who knows nothing. Every feature gets release notes. Documentation is code; review it. Ship docs with code, never after.

**File:** `src/keprix/personas/echo/SKILL.md`

---

## Persona 10: EMBER; Coach

**Phase:** OPS (continuous, not gated by sprint phase)
**Commands:** `/connect-chrome`, `/setup-browser-cookies`, `/setup-deploy`

### /connect-chrome; Chrome Connection

Connect Keprix to a running Chrome instance for browser automation. Detects Chrome DevTools Protocol port, establishes WebSocket connection, verifies connectivity. Output: connection status + available pages.

### /setup-browser-cookies; Browser Auth

Extract and save browser cookies for authenticated sessions. Used so Keprix can interact with authenticated web apps without re-login. Saves to `~/.keprix/cookies/` encrypted.

### /setup-deploy; Deployment Setup

Configure deployment for a project. Detect hosting platform (Vercel, Railway, Fly.io, bare metal), set up CI/CD, configure environment variables, run first deploy. Output deploy URL and dashboard link.

**Operating principles:** Make setup dead simple. One command should get you from clone to running. Cache everything that's expensive. Fail with actionable error messages, never mystery errors.

**File:** `src/keprix/personas/ember/SKILL.md`

---

## Persona 11: SCOUT; Governance

**Phase:** CONTINUOUS (runs across all phases)
**Commands:** `/careful`, `/freeze`, `/guard`, `/unfreeze`

These are safety commands that must work regardless of sprint phase. They map to `ScoutCommands` in the infrastructure layer (built in prompt 360).

| Command | Effect |
|---------|--------|
| `/careful` | Agent pauses before destructive ops (write, delete, terminal). Caution level raised. |
| `/freeze` | Lock all file writes. Read/search only. Agent cannot modify the filesystem. |
| `/guard` | Maximum safety. Every tool call requires explicit user approval. |
| `/unfreeze` | Release all locks. Return to normal operations. |

In addition to the safety commands, SCOUT's SKILL.md defines the governance philosophy:
- What constitutes a "destructive operation" (file writes, deletes, shell commands with `rm`, `mv`, `chmod`, package installs)
- When `/guard` should be automatically suggested (new dependency installs, production deploys, database migrations)
- Audit trail: all safety state changes are logged to gbrain
- The relationship with WARDEN: WARDEN finds threats, SCOUT enforces blocks

**Operating principles:** Safety is not optional. Default to locked, unlock with intention. Every safety state change is audited. Never override a user's explicit `/guard` or `/freeze`. Trust but verify; even when unfrozen, watch for anomalies.

**File:** `src/keprix/personas/scout/SKILL.md`

---

## Final Integration Test

After ALL 11 personas and ALL 5 infrastructure modules are built, run this comprehensive integration test.

**File:** `tests/skills/test_full_integration.py`

```python
"""Full integration test: all 11 personas + 5 infrastructure modules."""
import pytest
from src.keprix.skills import KeprixSkills

@pytest.fixture
def ks():
    return KeprixSkills(
        personas_dir="src/keprix/personas",
        gbrain_db=":memory:"  # Use in-memory DB for tests
    )

# ── Trigger routing ──────────────────────────────────────────────

@pytest.mark.parametrize("user_input,expected_persona,expected_command", [
    # NEXUS; THINK + SHIP
    ("/office-hours", "nexus", "/office-hours"),
    ("brainstorm this feature", "nexus", "/office-hours"),
    ("is this worth building", "nexus", "/office-hours"),
    ("/autoplan", "nexus", "/autoplan"),
    ("ship it", "nexus", "/ship"),
    ("deploy to production", "nexus", "/land-and-deploy"),
    ("/canary", "nexus", "/canary"),

    # COMPASS; PLAN
    ("/plan-ceo-review", "compass", "/plan-ceo-review"),
    ("should we pivot", "compass", "/plan-ceo-review"),
    ("kill this feature", "compass", "/plan-ceo-review"),
    ("narrow the scope", "compass", "/plan-ceo-review"),

    # FORGE; REVIEW + BUILD
    ("/review", "forge", "/review"),
    ("review my pull request", "forge", "/review"),
    ("code review this", "forge", "/review"),
    ("engineering feasibility check", "forge", "/plan-eng-review"),
    ("devex check", "forge", "/devex-review"),

    # BEACON; BUILD
    ("/design-consultation", "beacon", "/design-consultation"),
    ("design shotgun this", "beacon", "/design-shotgun"),
    ("generate html for landing page", "beacon", "/design-html"),
    ("/design-review", "beacon", "/design-review"),

    # CODEX; BUILD
    ("/codex", "codex", "/codex"),
    ("legal review please", "codex", "/codex"),
    ("check licenses", "codex", "/codex"),
    ("gdpr compliance check", "codex", "/codex"),

    # WARDEN; SECURITY
    ("/cso", "warden", "/cso"),
    ("security audit", "warden", "/cso"),
    ("vulnerability scan", "warden", "/cso"),
    ("/investigate", "warden", "/investigate"),
    ("root cause analysis", "warden", "/investigate"),

    # PRISM; TEST
    ("/qa", "prism", "/qa"),
    ("test this", "prism", "/qa"),
    ("run qa tests", "prism", "/qa"),
    ("/qa-only", "prism", "/qa-only"),

    # SAGE; REFLECT
    ("/retro", "sage", "/retro"),
    ("what did we learn this week", "sage", "/retro"),
    ("/benchmark", "sage", "/benchmark"),
    ("performance test", "sage", "/benchmark"),
    ("/learn", "sage", "/learn"),

    # ECHO; REFLECT
    ("/document-release", "echo", "/document-release"),
    ("generate release notes", "echo", "/document-release"),
    ("/document-generate", "echo", "/document-generate"),
    ("generate docs", "echo", "/document-generate"),

    # EMBER; OPS
    ("/connect-chrome", "ember", "/connect-chrome"),
    ("/setup-deploy", "ember", "/setup-deploy"),

    # SCOUT; CONTINUOUS
    ("/careful", "scout", "/careful"),
    ("/freeze", "scout", "/freeze"),
    ("/guard", "scout", "/guard"),
    ("/unfreeze", "scout", "/unfreeze"),
])
def test_trigger_routing(ks, user_input, expected_persona, expected_command):
    result = ks.triggers.route(user_input)
    assert result is not None, f"No route for: {user_input}"
    persona, command = result
    assert persona == expected_persona, f"Expected {expected_persona}, got {persona} for '{user_input}'"
    assert command == expected_command, f"Expected {expected_command}, got {command} for '{user_input}'"

# ── Unknown input falls through ───────────────────────────────────

def test_unknown_input_returns_none(ks):
    assert ks.triggers.route("random gibberish xyz123") is None
    assert ks.triggers.route("") is None
    assert ks.triggers.route("hello how are you") is None

# ── Scout safety commands work ────────────────────────────────────

def test_scout_freeze(ks):
    result = ks.handle_input("/freeze")
    assert ks.scout.should_block_write() == True
    assert ks.scout.frozen == True

def test_scout_unfreeze(ks):
    ks.scout.freeze()
    result = ks.handle_input("/unfreeze")
    assert ks.scout.should_block_write() == False
    assert ks.scout.caution_level == "normal"

def test_scout_guard(ks):
    ks.handle_input("/guard")
    assert ks.scout.caution_level == "guard"
    assert ks.scout.should_confirm("read_file") == True

def test_scout_careful(ks):
    ks.handle_input("/careful")
    assert ks.scout.should_confirm("write_file") == True
    assert ks.scout.should_confirm("read_file") == False

# ── Sprint flow ───────────────────────────────────────────────────

def test_sprint_phases_advance(ks):
    assert ks.sprint.current_phase.value == "think"
    ks.sprint.advance()
    assert ks.sprint.current_phase.value == "plan"
    ks.sprint.advance()
    assert ks.sprint.current_phase.value == "build"
    ks.sprint.advance()
    assert ks.sprint.current_phase.value == "review"

def test_sprint_phases_full_cycle(ks):
    for _ in range(7):  # think → plan → build → review → test → ship → reflect
        ks.sprint.advance()
    assert ks.sprint.current_phase.value == "reflect"
    ks.sprint.advance()  # wraps back
    assert ks.sprint.current_phase.value == "think"

def test_available_personas_by_phase(ks):
    # THINK: NEXUS + COMPASS
    assert set(ks.sprint.available_personas()) >= {"nexus", "compass"}

    # SHIP: only NEXUS
    ks.sprint.set_phase("ship")
    assert ks.sprint.available_personas() == ["nexus"]

    # BUILD: FORGE, CODEX, BEACON, EMBER
    ks.sprint.set_phase("build")
    assert set(ks.sprint.available_personas()) >= {"forge", "codex", "beacon", "ember"}

# ── Preamble loading ──────────────────────────────────────────────

def test_tier_1_loads_all_personas(ks):
    context = ks.preamble.tier_1_context()
    assert len(context) > 0
    assert "NEXUS" in context or "nexus" in context.lower()
    assert "FORGE" in context or "forge" in context.lower()
    assert "WARDEN" in context or "warden" in context.lower()

def test_tier_3_loads_specific_command(ks):
    context = ks.preamble.tier_3_context("/cso")
    assert len(context) > 500  # Should be substantial methodology
    assert "security" in context.lower() or "vulnerability" in context.lower()

# ── gbrain memory ─────────────────────────────────────────────────

def test_gbrain_save_and_retrieve(ks):
    from src.keprix.memory.gbrain import GBrain
    gb = GBrain(":memory:")
    gb.save("keprix", "nexus", "decision", "Approved feature X for v0.4")
    results = gb.query("keprix", "nexus", {"type": "decision", "limit": 5})
    assert "Approved feature X" in results

def test_gbrain_search(ks):
    from src.keprix.memory.gbrain import GBrain
    gb = GBrain(":memory:")
    gb.save("keprix", "warden", "incident", "SQL injection found in login form")
    gb.save("keprix", "warden", "incident", "XSS in comment field")
    results = gb.search("keprix", "SQL injection")
    assert len(results) >= 1
    assert "login form" in results[0]["content"]

# ── All 11 personas have valid SKILL.md ───────────────────────────

def test_all_personas_exist(ks):
    expected = {"nexus", "compass", "forge", "beacon", "codex",
                "warden", "prism", "sage", "echo", "ember", "scout"}
    loaded = set(ks.preamble._personas.keys())
    missing = expected - loaded
    assert not missing, f"Missing personas: {missing}"

# ── All 23 commands are triggerable ───────────────────────────────

def test_all_commands_listed(ks):
    commands = ks.triggers.list_commands()
    command_names = {c["command"] for c in commands}
    required = {
        "/office-hours", "/autoplan", "/ship", "/land-and-deploy", "/canary",     # NEXUS
        "/plan-ceo-review",                                                       # COMPASS
        "/review", "/plan-eng-review", "/devex-review",                           # FORGE
        "/design-consultation", "/design-shotgun", "/design-html",
        "/design-review", "/plan-design-review",                                  # BEACON
        "/codex",                                                                 # CODEX
        "/cso", "/investigate",                                                   # WARDEN
        "/qa", "/qa-only",                                                        # PRISM
        "/retro", "/benchmark", "/learn",                                         # SAGE
        "/document-release", "/document-generate",                                # ECHO
        "/connect-chrome", "/setup-browser-cookies", "/setup-deploy",             # EMBER
        "/careful", "/freeze", "/guard", "/unfreeze",                            # SCOUT
    }
    missing = required - command_names
    assert not missing, f"Missing commands in list_commands(): {missing}"
```

---

## Acceptance Criteria

- [ ] All 3 SKILL.md files parse without YAML errors
- [ ] ECHO: `/document-release` parses conventional commits. `/document-generate` extracts docstrings.
- [ ] EMBER: 3 operational commands for chrome, cookies, deploy.
- [ ] SCOUT: 4 safety commands with clear state model. Audit trail to gbrain.
- [ ] Integration test at `tests/skills/test_full_integration.py` exists
- [ ] **All 55 parametrized routing tests pass** (every trigger phrase routes correctly)
- [ ] **Scout safety state transitions work** (freeze → unfreeze, guard → normal)
- [ ] **Sprint flow cycles through all 7 phases** and wraps back to THINK
- [ ] **All 11 personas are loaded** and have valid SKILL.md
- [ ] **All 23+ commands are listed** in `list_commands()`
- [ ] **gbrain saves and retrieves** across different persona contexts

## Verification

```bash
cd /opt/lampp/htdocs/verlox/keprix

# Run the full integration test
python -m pytest tests/skills/test_full_integration.py -v

# Expected output: 60+ tests, all passing
```

Then:

```bash
# Smoke test: real routing simulation
python -c "
from src.keprix.skills import KeprixSkills
ks = KeprixSkills('src/keprix/personas', ':memory:')

# Walk through a full sprint
for phrase in ['brainstorm my new feature', 'is this worth building',
               'narrow the scope', 'engineering feasibility check',
               'design shotgun this landing page', 'legal review please',
               'review my pull request', 'security audit',
               'test this', 'qa-only please',
               'ship it', 'deploy to production',
               'what did we learn this week', 'generate release notes']:
    result = ks.triggers.route(phrase)
    status = f' → {result[0].upper():10s} {result[1]}' if result else ' NO ROUTE'
    print(f'{status:45s} | \"{phrase}\"')

# Scout test
ks.handle_input('/freeze')
print(f'\\n Freeze: block_write={ks.scout.should_block_write()}')
ks.handle_input('/unfreeze')
print(f'Done:  Unfreeze: block_write={ks.scout.should_block_write()}')
"
```

---

## File Manifest (All 5 Prompts Combined)

| # | File | Prompt |
|---|------|--------|
| 1 | `src/keprix/skills/preamble_loader.py` | 360 |
| 2 | `src/keprix/skills/trigger_engine.py` | 360 |
| 3 | `src/keprix/memory/gbrain.py` | 360 |
| 4 | `src/keprix/skills/sprint_flow.py` | 360 |
| 5 | `src/keprix/skills/scout_commands.py` | 360 |
| 6 | `src/keprix/skills/__init__.py` | 360 |
| 7 | `src/keprix/personas/nexus/SKILL.md` | 361 |
| 8 | `src/keprix/personas/compass/SKILL.md` | 361 |
| 9 | `src/keprix/personas/forge/SKILL.md` | 362 |
| 10 | `src/keprix/personas/beacon/SKILL.md` | 362 |
| 11 | `src/keprix/personas/codex/SKILL.md` | 362 |
| 12 | `src/keprix/personas/warden/SKILL.md` | 363 |
| 13 | `src/keprix/personas/prism/SKILL.md` | 363 |
| 14 | `src/keprix/personas/sage/SKILL.md` | 363 |
| 15 | `src/keprix/personas/echo/SKILL.md` | 364 |
| 16 | `src/keprix/personas/ember/SKILL.md` | 364 |
| 17 | `src/keprix/personas/scout/SKILL.md` | 364 |
| 18 | `tests/skills/test_full_integration.py` | 364 |
| 19 | `tests/skills/test_preamble_loader.py` | 360 |
| 20 | `tests/skills/test_trigger_engine.py` | 360 |
| 21 | `tests/memory/test_gbrain.py` | 360 |
| 22 | `tests/skills/test_sprint_flow.py` | 360 |
| 23 | `tests/skills/test_scout_commands.py` | 360 |

## Build Order

1. **Prompt 360**; Core infrastructure (all modules, no personas needed)
2. **Prompt 361**; NEXUS + COMPASS SKILL.md
3. **Prompt 362**; FORGE + BEACON + CODEX SKILL.md
4. **Prompt 363**; WARDEN + PRISM + SAGE SKILL.md
5. **Prompt 364**; ECHO + EMBER + SCOUT SKILL.md + integration test

Run the integration test after each prompt to catch regressions early.
