"""Workflow: Error paste loop (Prompt 270 Task 5.5).

User pastes an error → Keprix reads docs/self-knowledge hints → proposes a fix plan
→ asks for the next paste after the user retries.
"""

from __future__ import annotations

import re
from typing import Any


_HINTS: tuple[tuple[re.Pattern[str], str, list[str]], ...] = (
    (
        re.compile(r"ModuleNotFoundError|No module named", re.I),
        "Missing Python dependency",
        [
            "Confirm the package is listed in pyproject/requirements.",
            "Install into the active venv: `pip install <package>` or `pnpm`/`uv` equivalent.",
            "Re-run the same command and paste the new output.",
        ],
    ),
    (
        re.compile(r"Permission denied|EACCES|Operation not permitted", re.I),
        "Permission / sandbox block",
        [
            "Check Agent OS guardrails: path may be outside the workspace root.",
            "Avoid sudo; move the work into `~/.keprix/workspace`.",
            "If intentional, request approval for the destructive action.",
        ],
    ),
    (
        re.compile(r"Connection refused|ECONNREFUSED|Name or service not known", re.I),
        "Service / network connectivity",
        [
            "Confirm the target service is running (`keprix doctor`, health endpoints).",
            "Check host/port env vars in `.env`.",
            "Retry and paste the next error if it still fails.",
        ],
    ),
    (
        re.compile(r"API[_ ]?key|authentication|401|403 Forbidden|invalid.?token", re.I),
        "Auth / provider credentials",
        [
            "Do not paste secrets into chat; set them via `keprix model` / provider setup.",
            "Rotate the key if it was exposed.",
            "Re-test with a minimal prompt after credentials are fixed.",
        ],
    ),
    (
        re.compile(r"SyntaxError|IndentationError|TypeError|AttributeError", re.I),
        "Code / runtime exception",
        [
            "Open the file and line from the traceback.",
            "Ask Keprix to patch with a minimal diff; keep changes scoped.",
            "Re-run the failing command and paste the new traceback.",
        ],
    ),
)


def analyze_error_paste(*, error_text: str, context: str = "") -> dict[str, Any]:
    text = (error_text or "").strip()
    if not text:
        return {
            "status": "error",
            "workflow": "error-paste",
            "error": "error_text is required",
            "output": "Paste a traceback or error log to continue the loop.",
        }

    matched = None
    for pattern, title, steps in _HINTS:
        if pattern.search(text):
            matched = (title, steps)
            break
    if matched is None:
        matched = (
            "Generic failure",
            [
                "Extract the last 30 lines of the error (no secrets).",
                "Ask Keprix to search self-knowledge / docs for the exception name.",
                "Apply the smallest fix, re-run, paste the next error.",
            ],
        )

    title, steps = matched
    excerpt = "\n".join(text.splitlines()[-40:])
    loop = [
        {"id": "read", "title": "Read docs / classify error", "status": "done"},
        {"id": "plan", "title": f"Plan fix: {title}", "status": "done"},
        {"id": "apply", "title": "Apply minimal fix (human or agent)", "status": "todo"},
        {"id": "rerun", "title": "Re-run and paste the next error", "status": "todo"},
    ]

    markdown = [
        "# Error paste loop",
        "",
        f"Classified as: **{title}**",
        "",
        "## Pasted excerpt",
        "",
        "```",
        excerpt,
        "```",
        "",
        "## Fix plan",
    ]
    for idx, step in enumerate(steps, start=1):
        markdown.append(f"{idx}. {step}")
    if context.strip():
        markdown.extend(["", "## Extra context", "", context.strip()])
    markdown.extend(
        [
            "",
            "## Loop rule",
            "",
            "Do not debug by hand-editing files you do not understand.",
            "Apply the plan, re-run, paste the next error back into Keprix.",
        ]
    )

    return {
        "status": "ok",
        "workflow": "error-paste",
        "classification": title,
        "plan": steps,
        "steps": loop,
        "excerpt": excerpt,
        "output": "\n".join(markdown),
        "artifact": {
            "type": "error_paste_loop",
            "classification": title,
            "auto_skill": True,
        },
    }
