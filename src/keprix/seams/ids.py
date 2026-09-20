"""Seam identifiers and related constants."""

from __future__ import annotations

from typing import Literal

SeamId = Literal["fs", "shell", "memory", "llm", "subagent", "web"]

SEAM_IDS: tuple[SeamId, ...] = (
    "fs",
    "shell",
    "memory",
    "llm",
    "subagent",
    "web",
)

# Tool names historically bound to each seam (existing tools/registry entries).
# A provider swap is expected to move this related set together for consumers
# that resolve tools via the seam registry metadata.
SEAM_RELATED_TOOLS: dict[SeamId, tuple[str, ...]] = {
    "fs": (
        "read_file",
        "write_file",
        "search_files",
        "list_dir",
        "patch",
    ),
    "shell": (
        "terminal",
        "execute_code",
    ),
    "memory": (
        "memory",
        "conversation_search",
    ),
    "llm": (),  # model routing; not a single tool name
    "subagent": (
        "delegate_task",
    ),
    "web": (
        "web_search",
        "web_extract",
        "browser_navigate",
    ),
}
