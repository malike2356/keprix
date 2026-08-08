# Build Prompt: gstack Core Infrastructure for Keprix

> **Target:** Cursor or Claude Code
> **Source:** gstack by Garry Tan; https://github.com/garrytan/gstack
> **Input:** 11 persona SKILL.md files already exist at `src/keprix/personas/*/SKILL.md`
> **What this builds:** The runtime that loads personas, routes natural‑language triggers, manages sprint flow, handles memory, and wires Scout safety commands.

---

## Part 1; Preamble Loader

**What it is:** A tiered context-loading system. Every persona has a `preamble-tier` (1, 2, or 3) in its SKILL.md frontmatter. Tier 1 is always loaded. Tier 2 is loaded on demand (when the user enters a matching phase). Tier 3 is loaded only when a specific slash command is invoked.

**File:** `src/keprix/skills/preamble_loader.py`

### Requirements

```
class PreambleLoader:
    """
    Loads persona SKILL.md files by tier.

    Tier 1; always loaded (persona identity, core methodology)
    Tier 2; loaded when user enters the persona's sprint phase
    Tier 3; loaded only when a specific slash command is invoked
    """

    def __init__(self, personas_dir: str):
        # Scan all SKILL.md files under personas_dir
        # Parse YAML frontmatter (name, preamble-tier, triggers, allowed-tools, gbrain)
        # Index by tier and by persona name
        ...

    def tier_1_context(self) -> str:
        # Return concatenated tier-1 sections of ALL personas
        # These are short; identity sentences, not full methodologies
        ...

    def tier_2_context(self, active_phase: str) -> str:
        # Return tier-2 sections for personas assigned to active_phase
        # PHASES: think, plan, build, review, test, ship, reflect, ops, security, continuous
        ...

    def tier_3_context(self, command: str) -> str:
        # Return full SKILL.md body for the persona that owns this command
        # Map: /office-hours → NEXUS, /review → FORGE, /cso → WARDEN, etc.
        ...
```

### Acceptance criteria
- [ ] `preamble_loader.py` parses all 11 existing SKILL.md files without errors
- [ ] `preamble_loader.tier_1_context()` returns under 500 tokens of identity summaries
- [ ] `preamble_loader.tier_3_context("/cso")` returns WARDEN's full methodology
- [ ] Unknown persona or phase returns empty string (no crash)

---

## Part 2; Trigger Engine

**What it is:** Maps natural language (voice or text) to the correct slash command and persona. The user says "security audit" and WARDEN activates. They say "ship it" and NEXUS activates.

**File:** `src/keprix/skills/trigger_engine.py`

### Requirements

```
class TriggerEngine:
    """
    Routes user input to the correct persona and slash command.

    Input can be:
    - Exact slash command: /office-hours, /cso, /ship
    - Natural language: "is this worth building", "review my code", "what are the risks"
    - Short triggers: "ship it", "deploy", "audit"
    """

    def __init__(self, personas_dir: str):
        # Load all triggers from YAML frontmatter of each SKILL.md
        # Build a mapping: trigger phrase → (persona_name, command)
        ...

    def route(self, user_input: str) -> tuple[str, str] | None:
        """
        Returns (persona_name, command) if matched, else None.

        Matching logic (in priority order):
        1. Exact slash-command match: "/office-hours" → (nexus, /office-hours)
        2. Trigger phrase match (case-insensitive, substring):
           "security audit" → (warden, /cso)
        3. Keyword scoring: if input contains multiple keywords from one persona's
           trigger list, that persona wins.
        4. No match → return None (fall through to default assistant)
        """
        ...

    def list_commands(self) -> list[dict]:
        """Return all available commands with persona, phase, description."""
        ...
```

### Acceptance criteria
- [ ] `route("/cso")` → `("warden", "/cso")`
- [ ] `route("security audit now")` → `("warden", "/cso")`
- [ ] `route("ship it")` → `("nexus", "/ship")`
- [ ] `route("is this worth building")` → `("compass", "/plan-ceo-review")`
- [ ] `route("review my pull request")` → `("forge", "/review")`
- [ ] `route("generate the release notes")` → `("echo", "/document-release")`
- [ ] `route("random gibberish xyz")` → `None`
- [ ] `list_commands()` returns all 23+ commands with correct persona mapping

---

## Part 3; gbrain Memory System

**What it is:** Persistent memory with context queries. Each SKILL.md defines `gbrain.context_queries`; a list of queries that pre-load relevant context before the persona runs. gbrain stores session summaries, decisions, and knowledge across sessions.

**File:** `src/keprix/memory/gbrain.py`

### Requirements

```
class GBrain:
    """
    Persistent memory store. Saves and retrieves context by project, persona, and type.

    Storage: SQLite database at ~/.keprix/gbrain.db
    Schema:
      - id, project, persona, type, content, embedding, created_at, updated_at
      - type: session_summary, decision, knowledge, retro, review, incident
    """

    def __init__(self, db_path: str = "~/.keprix/gbrain.db"):
        ...

    def save(self, project: str, persona: str, type: str, content: str):
        """Save a memory entry."""
        ...

    def query(self, project: str, persona: str, filters: dict) -> str:
        """
        Execute context_queries from a persona's SKILL.md.

        Supported filter keys:
        - type: filter by memory type
        - sort: "updated_at_desc" | "created_at_desc" | "relevance"
        - limit: max results (default 5)

        Returns formatted markdown string ready for prompt injection.
        """
        ...

    def search(self, project: str, query: str, limit: int = 5) -> list[dict]:
        """Full-text search across all entries for a project."""
        ...

    def get_recent(self, project: str, persona: str, days: int = 7) -> str:
        """Get recent entries from last N days, formatted for context injection."""
        ...
```

### Acceptance criteria
- [ ] `gbrain.db` created on first use
- [ ] `save("keprix", "nexus", "decision", "Approved feature X for v0.4")` persists
- [ ] `query("keprix", "nexus", {"type": "decision", "limit": 5})` returns the decision
- [ ] Search across projects works
- [ ] Context queries from SKILL.md frontmatter execute correctly (e.g. NEXUS's "product decisions" query)
- [ ] Entries older than 90 days are not returned unless explicitly requested

---

## Part 4; Sprint Flow Engine

**What it is:** The guided 7-phase workflow: Think → Plan → Build → Review → Test → Ship → Reflect. Users can be in exactly one phase at a time. Phases gate which personas are active and which commands are available.

**File:** `src/keprix/skills/sprint_flow.py`

### Requirements

```
from enum import Enum

class SprintPhase(Enum):
    THINK = "think"       # NEXUS, COMPASS
    PLAN = "plan"         # NEXUS, COMPASS, FORGE, BEACON
    BUILD = "build"       # FORGE, CODEX, BEACON, EMBER
    REVIEW = "review"     # FORGE, WARDEN, BEACON
    TEST = "test"         # PRISM, SAGE, FORGE
    SHIP = "ship"         # NEXUS
    REFLECT = "reflect"   # SAGE, ECHO

PHASE_ORDER = [
    SprintPhase.THINK,
    SprintPhase.PLAN,
    SprintPhase.BUILD,
    SprintPhase.REVIEW,
    SprintPhase.TEST,
    SprintPhase.SHIP,
    SprintPhase.REFLECT,
]

class SprintFlow:
    def __init__(self, gbrain: GBrain):
        self.current_phase = SprintPhase.THINK
        self.gbrain = gbrain
        ...

    def advance(self) -> SprintPhase:
        """Move to next phase. Wraps from REFLECT back to THINK."""
        ...

    def set_phase(self, phase: SprintPhase):
        """Jump to any phase (e.g. skip THINK if already planned)."""
        ...

    def available_personas(self) -> list[str]:
        """Return persona names active in current phase."""
        ...

    def available_commands(self) -> list[str]:
        """Return slash commands available in current phase."""
        ...

    def phase_summary(self) -> str:
        """Return a short summary: current phase, available personas/commands, next phase."""
        ...

    def checkpoint(self):
        """Save current phase + context to gbrain so next session resumes here."""
        ...
```

### Acceptance criteria
- [ ] Starts in THINK phase
- [ ] `advance()` walks through all 7 phases in order
- [ ] `available_personas()` for BUILD returns ["forge", "codex", "beacon", "ember"]
- [ ] `available_personas()` for SHIP returns ["nexus"]
- [ ] `set_phase(SprintPhase.SHIP)` works (skip-ahead)
- [ ] `checkpoint()` saves to gbrain and `SprintFlow(gbrain)` restores from gbrain

---

## Part 5; Scout Safety Wiring

**What it is:** Map Scout's 4 safety commands (`/careful`, `/freeze`, `/guard`, `/unfreeze`) to actual enforcement. These commands must work regardless of current sprint phase; SCOUT runs continuously.

**File:** `src/keprix/skills/scout_commands.py`

### Requirements

```
class ScoutCommands:
    """
    Continuous safety layer. Independent of sprint phase.

    /careful; Raise caution level. Agent pauses before destructive ops.
    /freeze; Lock all file writes. Agent can read/search but not modify.
    /guard; Enable maximum safety. All tool calls require confirmation.
    /unfreeze; Release any active lock or guard.
    """

    CAUTION_LEVELS = ["normal", "careful", "guard"]

    def __init__(self):
        self.caution_level = "normal"
        self.frozen = False

    def careful(self) -> str:
        """Set caution to 'careful'. Agent asks before file writes and deletes."""
        self.caution_level = "careful"
        return "WARNING:  Caution mode active. All destructive operations require confirmation."

    def freeze(self) -> str:
        """Lock all file writes. Read-only mode."""
        self.frozen = True
        return " Freeze active. All file writes blocked. Read/search only."

    def guard(self) -> str:
        """Maximum safety. Every tool call requires explicit user approval."""
        self.caution_level = "guard"
        return " Guard mode active. All tool calls require explicit approval."

    def unfreeze(self) -> str:
        """Release all locks."""
        self.caution_level = "normal"
        self.frozen = False
        return "Done:  All locks released. Normal operations resumed."

    def should_block_write(self) -> bool:
        """Returns True if file writes should be blocked."""
        return self.frozen

    def should_confirm(self, tool_name: str) -> bool:
        """Returns True if this tool call requires user confirmation."""
        if self.caution_level == "guard":
            return True
        if self.caution_level == "careful" and tool_name in ("write_file", "patch", "terminal", "process"):
            return True
        return False

    def status(self) -> str:
        """Return current safety status as a single line."""
        ...
```

### Acceptance criteria
- [ ] `scout.freeze()` → `should_block_write()` returns True, `should_confirm()` unchanged
- [ ] `scout.guard()` → `should_confirm("read_file")` returns True (every tool)
- [ ] `scout.careful()` → `should_confirm("write_file")` returns True, `should_confirm("read_file")` returns False
- [ ] `scout.unfreeze()` → all methods return False, caution_level is "normal"
- [ ] `/careful`, `/freeze`, `/guard`, `/unfreeze` are recognized by TriggerEngine and route to SCOUT

---

## Part 6; Integration: Wire Everything Together

**File:** `src/keprix/skills/__init__.py`

Create a single entry point that ties the five components together:

```
from .preamble_loader import PreambleLoader
from .trigger_engine import TriggerEngine
from .sprint_flow import SprintFlow, SprintPhase
from .scout_commands import ScoutCommands

class KeprixSkills:
    """Top-level orchestrator for the Keprix skill system."""

    def __init__(self, personas_dir: str, gbrain_db: str):
        self.preamble = PreambleLoader(personas_dir)
        self.triggers = TriggerEngine(personas_dir)
        self.sprint = SprintFlow(gbrain_db)
        self.scout = ScoutCommands()

    def handle_input(self, user_text: str) -> dict:
        """
        Main entry point. Given user input:
        1. Check if it's a Scout safety command → handle immediately
        2. Route to persona via TriggerEngine
        3. Load context via PreambleLoader (tier 2 + tier 3)
        4. Execute command in current sprint phase
        5. Return persona name, command, context, and sprint status
        """
        ...

    def phase_summary(self) -> str:
        """Human-readable summary of current sprint state."""
        ...
```

### Acceptance criteria
- [ ] `handle_input("/freeze")` returns scout command with frozen=True
- [ ] `handle_input("ship it")` in SHIP phase returns NEXUS `/ship` with full context
- [ ] `handle_input("ship it")` in THINK phase returns error: "Not in SHIP phase. Advance first."
- [ ] `handle_input("audit my code")` routes to WARDEN `/cso`
- [ ] `handle_input("does this look good")` routes to BEACON `/design-review`
- [ ] `handle_input("what did we learn this week")` routes to SAGE `/retro`
- [ ] Unknown input returns default assistant mode (no persona override)

---

## File Manifest

| # | File | What |
|---|------|------|
| 1 | `src/keprix/skills/preamble_loader.py` | Tiered context loading (tier 1/2/3) |
| 2 | `src/keprix/skills/trigger_engine.py` | Natural language → slash command routing |
| 3 | `src/keprix/memory/gbrain.py` | Persistent memory with context queries |
| 4 | `src/keprix/skills/sprint_flow.py` | 7-phase guided workflow |
| 5 | `src/keprix/skills/scout_commands.py` | Scout safety: /careful, /freeze, /guard, /unfreeze |
| 6 | `src/keprix/skills/__init__.py` | Top-level orchestrator + wire everything together |
| 7 | `tests/skills/test_preamble_loader.py` | Tests for preamble loader |
| 8 | `tests/skills/test_trigger_engine.py` | Tests for trigger engine |
| 9 | `tests/memory/test_gbrain.py` | Tests for gbrain |
| 10 | `tests/skills/test_sprint_flow.py` | Tests for sprint flow |
| 11 | `tests/skills/test_scout_commands.py` | Tests for scout commands |
| 12 | `tests/skills/test_integration.py` | Integration tests (all 5 components) |

## Build Order

1. `preamble_loader.py` (needed by everything else)
2. `gbrain.py` (needed by sprint_flow)
3. `trigger_engine.py` (standalone)
4. `scout_commands.py` (standalone)
5. `sprint_flow.py` (needs gbrain)
6. `__init__.py` (needs all 4 above)
7. Tests (after each module)

## Verification

After building all 6 modules:

```bash
cd /opt/lampp/htdocs/verlox/keprix
python -m pytest tests/skills/ tests/memory/ -v
```

All tests must pass. Then run the integration smoke test:

```bash
python -c "
from src.keprix.skills import KeprixSkills
ks = KeprixSkills('src/keprix/personas', '~/.keprix/gbrain.db')

# Test trigger routing
assert ks.triggers.route('security audit')[0] == 'warden'
assert ks.triggers.route('ship it')[0] == 'nexus'

# Test scout commands
ks.scout.freeze()
assert ks.scout.should_block_write() == True
ks.scout.unfreeze()
assert ks.scout.should_block_write() == False

# Test sprint flow
assert ks.sprint.current_phase.value == 'think'
ks.sprint.advance()
assert ks.sprint.current_phase.value == 'plan'

print('All integration smoke tests passed.')
"
```
