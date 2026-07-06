"""Read-only Keprix codebase awareness for the web chat workspace."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from keprix.coding.repo_map import build_repo_map
from keprix.security.redactor import get_redactor

_MAX_TOTAL_CHARS = 14_000
_MAX_FILE_CHARS = 6_000

_SECURITY_RULES = """Security rules (mandatory):
- You are Keprix in the web chat workspace. Answer from the product brief and codebase snapshot below.
- Never quote, reveal, reconstruct, or guess API keys, passwords, JWT/session secrets, vault keys, or .env values.
- Never dump .env, auth.json, credential stores, private keys, or other secret file contents.
- If asked for secrets, refuse briefly and tell the user to use Dashboard > Settings or their local .env (names only, never values).
- Do not expose other users' sessions, messages, or private data.
- Prefer concise architecture answers with file paths; avoid pasting large code blocks unless the user asks for a specific public file.
- If the snapshot does not contain enough detail, say what is missing instead of inventing modules or routes."""

_WORKSPACE_IDENTITY = """You are Keprix, the self-hosted MIT-licensed AI agent OS running in this workspace.
You are not a generic chatbot and you are not a third-party model pretending to be helpful.
When users ask who you are, what you can do, or how mutation works, answer from the Keprix product brief below.
Do not claim you lack information about Keprix or this workspace when the brief already covers it."""

_CAPABILITIES_BRIEF = """## Keprix in this workspace

**What Keprix is**
- Self-hosted agent OS: tool-calling loops, memory, skills, channels, and workspace modules on your machine or VPS
- Supports many LLM providers (DeepSeek, Anthropic, OpenAI, Gemini, Groq, Ollama, OpenRouter, custom OpenAI-compatible endpoints)

**Workspace surfaces**
- Web chat (this UI), admin dashboard, documents, notes, tasks, calendar, contacts, research, opportunities, playbooks, domain packs, evals
- CLI/TUI (`keprix chat`, `keprix --tui`), messaging gateway (Telegram, Discord, and more), REST API, Python SDK

**Agent capabilities (full runtime)**
- Registered tools: filesystem, terminal, web search/extract, browser, delegation/subagents, MCP servers, skills, cron, memory, workspace APIs
- Tool availability depends on configured API keys, enabled toolsets, and admin settings
- Streaming responses, slash commands, session history, model switching

**Mutation engine (self-coding)**
- When no existing tool can complete a task, Keprix synthesizes a new Python tool, runs it in a sandbox, and proposes it for owner approval
- Approved tools install live without restarting the runtime; rejections stay in the audit log
- Pending mutations surface in chat and in Dashboard > Mutations
- This is a core Keprix feature, not a hypothetical future capability

**Web search and external APIs**
- Internet search uses configured providers and tools (for example SearXNG, Tavily, or provider-native search), not ad-hoc keys pasted in chat
- If a user offers an API key in chat, explain they should add it in Dashboard > Settings or `.env`, then restart; do not pretend you can silently wire it mid-conversation

**This web chat path**
- Code-aware Q&A with repository context plus the product brief above
- Messages starting with `/` run slash commands (for example `/status`, `/help`)
- For full tool execution (terminal, file edits, mutations in the live loop), use the agent CLI, embedded TUI, or gateway; point users there when they need hands-on execution"""

_CONTEXT_FILES: tuple[tuple[str, int], ...] = (
    ("README.md", 3_500),
    ("docs/features/chat.md", 3_000),
    ("docs/features/self-coding-agent.md", 2_000),
    ("src/keprix/AGENTS.md", 4_000),
)


def codebase_awareness_enabled() -> bool:
    raw = os.getenv("KEPRIX_CODEBASE_AWARENESS", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def resolve_repo_root() -> Path | None:
    explicit = os.getenv("KEPRIX_REPO_ROOT", "").strip()
    if explicit:
        path = Path(explicit).expanduser().resolve()
        return path if path.is_dir() else None

    package_root = Path(__file__).resolve().parents[3]
    if _looks_like_keprix_root(package_root):
        return package_root

    cwd = Path.cwd().resolve()
    if _looks_like_keprix_root(cwd):
        return cwd

    return None


def _looks_like_keprix_root(path: Path) -> bool:
    return (path / "README.md").is_file() and (path / "src" / "keprix").is_dir()


def _read_context_file(root: Path, rel: str, *, max_chars: int) -> str | None:
    path = (root / rel).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n\n[truncated]"
    return get_redactor().redact(text)


@lru_cache(maxsize=1)
def build_codebase_system_prompt() -> str:
    if not codebase_awareness_enabled():
        return ""

    root = resolve_repo_root()
    if root is None:
        return get_redactor().redact(
            "\n".join(
                [
                    _WORKSPACE_IDENTITY,
                    _SECURITY_RULES,
                    _CAPABILITIES_BRIEF,
                    "Codebase snapshot: unavailable (KEPRIX_REPO_ROOT not set and install root not detected).",
                ]
            )
        )

    redactor = get_redactor()
    sections: list[str] = [
        _WORKSPACE_IDENTITY,
        _SECURITY_RULES,
        _CAPABILITIES_BRIEF,
        f"Install root: {root}",
    ]

    try:
        repo_map = build_repo_map(root, max_files=120)
        sections.extend(["", "## Repository map", "```text", repo_map.compact_text(max_files=35), "```"])
    except Exception:
        sections.append("Repository map: unavailable.")

    for rel, limit in _CONTEXT_FILES:
        content = _read_context_file(root, rel, max_chars=min(limit, _MAX_FILE_CHARS))
        if content:
            sections.extend(["", f"## {rel}", content])

    prompt = "\n".join(sections).strip()
    if len(prompt) > _MAX_TOTAL_CHARS:
        prompt = prompt[:_MAX_TOTAL_CHARS].rstrip() + "\n\n[context truncated]"
    return redactor.redact(prompt)


def redact_assistant_text(text: str) -> str:
    return get_redactor().redact(text)
