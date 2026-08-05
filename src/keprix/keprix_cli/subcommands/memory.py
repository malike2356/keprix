"""``keprix memory`` subcommand parser.

Extracted from ``keprix_cli/main.py:main()`` (god-file Phase 2 follow-up).
Handler injected to avoid importing ``main``.
"""

from __future__ import annotations

from typing import Callable


def build_memory_parser(subparsers, *, cmd_memory: Callable) -> None:
    """Attach the ``memory`` subcommand to ``subparsers``."""
    memory_parser = subparsers.add_parser(
        "memory",
        help="Configure external memory provider",
        description=(
            "Set up and manage external memory provider plugins.\n\n"
            "Available providers: honcho, openviking, mem0, hindsight,\n"
            "holographic, retaindb, byterover.\n\n"
            "Only one external provider can be active at a time.\n"
            "Built-in memory (MEMORY.md/USER.md) is always active."
        ),
    )
    memory_sub = memory_parser.add_subparsers(dest="memory_command")
    _setup_parser = memory_sub.add_parser(
        "setup", help="Interactive provider selection and configuration"
    )
    _setup_parser.add_argument(
        "provider",
        nargs="?",
        default=None,
        help="Provider to configure directly (e.g. honcho), skipping the picker",
    )
    memory_sub.add_parser("status", help="Show current memory provider config")
    memory_sub.add_parser("off", help="Disable external provider (built-in only)")
    _reset_parser = memory_sub.add_parser(
        "reset",
        help="Erase all built-in memory (MEMORY.md and USER.md)",
    )
    _reset_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    _reset_parser.add_argument(
        "--target",
        choices=["all", "memory", "user"],
        default="all",
        help="Which store to reset: 'all' (default), 'memory', or 'user'",
    )
    index_self = memory_sub.add_parser(
        "index-self",
        help="Index Keprix docs, capabilities, and codebase into shared self-knowledge RAG",
    )
    index_self.add_argument("--docs-only", action="store_true", help="Skip codebase file indexing")
    index_self.add_argument("--codebase-only", action="store_true", help="Skip curated product docs")
    index_self.add_argument("--max-files", type=int, default=2000, help="Max codebase files to index")
    search_self = memory_sub.add_parser(
        "search-self",
        help="Search the shared Keprix self-knowledge RAG corpus",
    )
    search_self.add_argument("query", help="Natural-language query about Keprix")
    search_self.add_argument("--limit", type=int, default=8)
    memory_parser.set_defaults(func=cmd_memory)
