# keprix - Prompt 43: Coding Posture Detection

## Context

Reference: `planning/agents-to-adopt/hermes-agent/agent/coding_context.py`.

keprix has a general-purpose agent loop (Prompt 03), a full tool registry (Prompt 05), and memory (Prompt 06). When a user runs keprix inside a code workspace - a directory with a git repo, a package.json, a pyproject.toml - the agent should shift into a different operating posture without the user having to tell it every session.

The posture change is not cosmetic. It affects:
- Which tools are surfaced prominently (code tools vs general tools)
- What the system prompt includes (a live git and workspace snapshot)
- How the agent routes model selection (prefer code-capable models)
- What child agents inherit (coding posture propagates to subagents)
- How memory review is weighted (code patterns, file paths, project conventions worth saving)

The single constraint that shapes everything: **the posture must be resolved once and frozen before the conversation starts, and must never be re-derived mid-conversation.** Re-deriving per-turn would invalidate the prompt cache and multiply cost for every user who has a long coding session. The workspace snapshot goes in the stable tier of the system prompt, not the dynamic tier.

This prompt builds the `CodingContext` module: posture detection, snapshot building, system prompt injection, and model routing hint.

---

## File Structure

```
keprix/backend/agent/
    coding_context.py       - posture detection, snapshot, mode resolution
    context_profiles.py     - ContextProfile registry (coding, general, research)

keprix/tests/agent/
    test_coding_context.py
```

---

## Context Profiles

```python
# keprix/backend/agent/context_profiles.py

from dataclasses import dataclass, field
from typing import Literal

RuntimeModeName = Literal["general", "coding", "research"]

@dataclass(frozen=True)
class ContextProfile:
    name: RuntimeModeName
    # System prompt blocks to inject when this profile is active.
    # These are STABLE blocks (go in the cached tier, not the per-turn tier).
    system_blocks: list[str]
    # Tool categories to surface in order (first = most prominent).
    toolset_priority: list[str]
    # Hint for the LLM provider router (Prompt 04). Not a hard override.
    model_hint: str | None = None
    # Memory review weighting. Passed to the background review fork (Prompt 03).
    memory_weight: str = "default"


PROFILES: dict[RuntimeModeName, ContextProfile] = {
    "general": ContextProfile(
        name="general",
        system_blocks=[],  # no extra blocks; standard system prompt only
        toolset_priority=["core", "web", "files", "messaging"],
        model_hint=None,
        memory_weight="default",
    ),
    "coding": ContextProfile(
        name="coding",
        system_blocks=[
            # Injected into stable system prompt tier at session start.
            # Builder inserts the live workspace snapshot here (see CodingContext.build_snapshot).
            "__WORKSPACE_SNAPSHOT__",
        ],
        toolset_priority=["code", "terminal", "files", "core"],
        model_hint="code-capable",    # provider router interprets this
        memory_weight="code-focused", # background review saves project conventions
    ),
    "research": ContextProfile(
        name="research",
        system_blocks=[],
        toolset_priority=["web", "rag", "files", "core"],
        model_hint=None,
        memory_weight="research-focused",
    ),
}
```

---

## CodingContext Module

```python
# keprix/backend/agent/coding_context.py

import os
import subprocess
from pathlib import Path
from dataclasses import dataclass
from keprix.backend.agent.context_profiles import ContextProfile, PROFILES, RuntimeModeName

# Detection signals in order of specificity.
# First match wins. All paths are checked relative to the working directory.
CODING_WORKSPACE_SIGNALS = [
    ".git",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "build.gradle",
    "pom.xml",
    "CMakeLists.txt",
    "Makefile",
    ".claude",     # Claude Code workspace
    ".hermes",     # Hermes workspace
]


@dataclass(frozen=True)
class WorkspaceSnapshot:
    """
    A frozen snapshot of the workspace at session start.
    Baked into the stable system prompt tier once; never re-derived per turn.
    """
    cwd: str
    is_git_repo: bool
    current_branch: str | None
    has_uncommitted_changes: bool | None
    recent_files: list[str]       # up to 10 recently modified tracked files
    primary_language: str | None  # best-guess from file extensions
    note: str                     # tell the model to re-check git before acting


@dataclass(frozen=True)
class RuntimeMode:
    """Resolved posture for this session. Immutable."""
    name: RuntimeModeName
    profile: ContextProfile
    snapshot: WorkspaceSnapshot | None  # only set when name == "coding"

    def system_blocks(self) -> list[str]:
        """Returns rendered system prompt blocks for this mode."""
        blocks = []
        for block in self.profile.system_blocks:
            if block == "__WORKSPACE_SNAPSHOT__" and self.snapshot:
                blocks.append(self._render_snapshot(self.snapshot))
            elif block != "__WORKSPACE_SNAPSHOT__":
                blocks.append(block)
        return blocks

    def toolset_selection(self) -> list[str]:
        return self.profile.toolset_priority

    def _render_snapshot(self, snap: WorkspaceSnapshot) -> str:
        lines = [
            "## Workspace Snapshot (recorded at session start)",
            f"Directory: {snap.cwd}",
        ]
        if snap.is_git_repo:
            lines.append(f"Branch: {snap.current_branch or 'unknown'}")
            if snap.has_uncommitted_changes is True:
                lines.append("Uncommitted changes: yes")
            elif snap.has_uncommitted_changes is False:
                lines.append("Uncommitted changes: no")
            if snap.recent_files:
                lines.append("Recently modified files:")
                for f in snap.recent_files:
                    lines.append(f"  {f}")
        if snap.primary_language:
            lines.append(f"Primary language: {snap.primary_language}")
        lines.append(snap.note)
        return "\n".join(lines)


class CodingContext:
    """
    Resolves the runtime mode for a session.
    Called once at session start. Result is frozen and injected into the system prompt.
    """

    def resolve(
        self,
        cwd: str | None = None,
        forced_mode: RuntimeModeName | None = None,
    ) -> RuntimeMode:
        """
        Resolve the runtime mode.

        forced_mode: set by user config `agent.mode` or the `/mode` slash command.
        If not forced, auto-detect from the working directory.
        The resolved mode is immutable for the lifetime of the session.
        """
        if forced_mode:
            mode_name = forced_mode
        else:
            mode_name = self._detect(cwd or os.getcwd())

        profile = PROFILES[mode_name]
        snapshot = self.build_snapshot(cwd or os.getcwd()) if mode_name == "coding" else None

        return RuntimeMode(name=mode_name, profile=profile, snapshot=snapshot)

    def _detect(self, cwd: str) -> RuntimeModeName:
        """Detects mode from the working directory. Returns 'general' if no coding signals found."""
        path = Path(cwd)
        for signal in CODING_WORKSPACE_SIGNALS:
            if (path / signal).exists():
                return "coding"
        return "general"

    def build_snapshot(self, cwd: str) -> WorkspaceSnapshot:
        """
        Build the workspace snapshot. Uses subprocess git calls.
        All git calls use a 2-second timeout. Failure is silent (returns None fields).
        This is called ONCE at session start, never per-turn.
        """
        path = Path(cwd)
        is_git = (path / ".git").exists()
        branch = None
        has_uncommitted = None
        recent_files: list[str] = []
        primary_language = None

        if is_git:
            branch = self._run_git(cwd, ["rev-parse", "--abbrev-ref", "HEAD"])
            status = self._run_git(cwd, ["status", "--porcelain"])
            has_uncommitted = bool(status and status.strip())
            recent_raw = self._run_git(cwd, ["diff", "--name-only", "HEAD~5..HEAD", "--"])
            if recent_raw:
                recent_files = [f.strip() for f in recent_raw.splitlines() if f.strip()][:10]

        primary_language = self._detect_primary_language(path)

        return WorkspaceSnapshot(
            cwd=cwd,
            is_git_repo=is_git,
            current_branch=branch,
            has_uncommitted_changes=has_uncommitted,
            recent_files=recent_files,
            primary_language=primary_language,
            note=(
                "This snapshot was recorded at session start. "
                "Branch and file state may have changed. "
                "Run git commands to verify current state before acting."
            ),
        )

    def _run_git(self, cwd: str, args: list[str]) -> str | None:
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=2,
            )
            return result.stdout if result.returncode == 0 else None
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    def _detect_primary_language(self, path: Path) -> str | None:
        """
        Best-guess primary language from file extensions in the top-level directory.
        Not recursive - just a quick signal.
        """
        ext_map = {
            ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript",
            ".js": "JavaScript", ".jsx": "JavaScript", ".rs": "Rust",
            ".go": "Go", ".java": "Java", ".kt": "Kotlin",
            ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".cpp": "C++",
            ".c": "C", ".swift": "Swift",
        }
        counts: dict[str, int] = {}
        try:
            for f in path.iterdir():
                if f.is_file() and f.suffix in ext_map:
                    lang = ext_map[f.suffix]
                    counts[lang] = counts.get(lang, 0) + 1
        except OSError:
            return None
        return max(counts, key=counts.__getitem__) if counts else None
```

---

## Integration Into Agent Loop

In `keprix/backend/agent/agent_loop.py`, resolve the mode once at session initialization:

```python
# In AgentSession.__init__ or session_start():

from keprix.backend.agent.coding_context import CodingContext

coding_context = CodingContext()
self.runtime_mode = coding_context.resolve(
    cwd=session_config.cwd,
    forced_mode=workspace_config.get("agent.mode"),  # from workspace settings
)

# Inject stable system prompt blocks from the resolved mode:
self.system_prompt_stable_blocks.extend(self.runtime_mode.system_blocks())

# Tell the tool registry which category order to use:
self.tool_registry.set_priority(self.runtime_mode.toolset_selection())

# Pass the model hint to the provider router (Prompt 04):
self.provider_router.set_mode_hint(self.runtime_mode.profile.model_hint)

# Pass the memory weight to the background review fork (Prompt 03):
self.background_review_config.memory_weight = self.runtime_mode.profile.memory_weight
```

**Cache safety rule:** `runtime_mode` is resolved once and stored on the session object. It is never re-derived per turn. If the user switches mode mid-session with `/mode coding`, the change takes effect only on the next session (same contract as `/skills install` without `--now`). A comment in `agent_loop.py` must state this explicitly so future contributors do not break it.

---

## Subagent Propagation

When the agent spawns a subagent (Prompt 03), the parent's runtime mode propagates automatically:

```python
# In subagent spawning logic:

def spawn_subagent(self, prompt: str, tools: list | None = None) -> SubagentHandle:
    return SubagentHandle(
        prompt=prompt,
        tools=tools or self.runtime_mode.toolset_selection(),
        system_blocks=self.runtime_mode.system_blocks(),
        model_hint=self.runtime_mode.profile.model_hint,
        # Subagent does NOT rebuild the workspace snapshot; it inherits the parent's.
        inherited_snapshot=self.runtime_mode.snapshot,
    )
```

Subagents run with the same posture as the parent. They do not re-detect the environment.

---

## Slash Command

`/mode [general|coding|research]`

Sets `agent.mode` in the workspace config. Takes effect next session. Current session is unaffected (frozen posture).

```
/mode coding    -> workspace config: agent.mode = "coding"
/mode           -> shows current resolved mode and how it was detected (auto or forced)
```

---

## Workspace Config Key

`agent.mode`: `"general" | "coding" | "research" | null`

`null` means auto-detect (default). Stored in workspace config (Prompt 10). Can be set via UI in workspace settings or via `/mode` slash command.

---

## Acceptance Criteria

- `CodingContext.resolve(cwd)` returns `RuntimeMode(name="coding", ...)` when `cwd` contains a `.git` directory.
- `CodingContext.resolve(cwd)` returns `RuntimeMode(name="general", ...)` when `cwd` has no coding signals.
- `CodingContext.resolve(forced_mode="research")` returns `RuntimeMode(name="research", ...)` regardless of what is in `cwd`.
- `RuntimeMode.system_blocks()` returns a rendered workspace snapshot block when mode is `coding` and snapshot is not None.
- `RuntimeMode.system_blocks()` returns an empty list when mode is `general`.
- `build_snapshot()` completes in under 3 seconds even when git is not installed (timeouts silently, returns snapshot with `is_git_repo=False`).
- `build_snapshot()` is called exactly once per session, not per turn. Verified by the test: mock `_run_git` and assert call count is 1 after 3 simulated turns.
- The workspace snapshot block contains the literal note about re-checking git state before acting.
- `/mode coding` updates workspace config and a follow-up `/mode` shows `mode: coding (forced)`.
- Subagents spawned from a coding-mode session have `model_hint = "code-capable"` without re-detecting the environment.
- `_detect_primary_language` returns `"Python"` for a directory containing 3 `.py` files and 1 `.js` file.
