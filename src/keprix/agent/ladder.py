"""Ponytail ladder prompt injection."""

from __future__ import annotations

from pathlib import Path


PONYTAIL_LADDER_PROMPT = """## Code generation: climb the ladder

Before writing any code, stop at the first rung that holds:

1. Does this need to be built at all? (YAGNI)
2. Does it already exist in this codebase? Reuse the helper, util, or pattern that's already here.
3. Does the standard library already do this? Use it.
4. Does a native platform feature cover it? Use it.
5. Does an already-installed dependency solve it? Use it.
6. Can this be one line? Make it one line.
7. Only then: write the minimum code that works.

The ladder runs after you understand the problem, not instead of it: read the task and touched code, trace the real flow end to end, then climb.

Rules:
- No abstractions that weren't explicitly requested.
- No new dependency if it can be avoided.
- No boilerplate nobody asked for.
- Deletion over addition. Boring over clever. Fewest files possible.
- Shortest working diff wins, after you understand the problem.
- Mark intentional simplifications with a `ponytail:` comment that names the ceiling and upgrade path.

Not lazy about: input validation at trust boundaries, data-loss-preventing error handling, security, accessibility, and anything explicitly requested.
"""


CODING_SYSTEM_PROMPT_EXTENSION = f"""You are a coding agent inside Keprix.

{PONYTAIL_LADDER_PROMPT}

When generating code, always climb the ladder first, reuse existing patterns, prefer stdlib, avoid dependencies, and create new files only when existing files cannot reasonably hold the change.
"""


def bundled_ladder_path() -> Path:
    return Path(__file__).resolve().parents[1] / "skills" / "coding" / "ponytail" / "rules" / "ladder.md"


def build_coding_prompt(base_prompt: str = "") -> str:
    return "\n\n".join(part for part in [base_prompt.strip(), CODING_SYSTEM_PROMPT_EXTENSION] if part)
