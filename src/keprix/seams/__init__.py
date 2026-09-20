"""Keprix capability seams: Definition / Provider / Consumer contracts.

Formalises swappable capabilities (fs, shell, memory, llm, subagent, web)
without a Cordis rewrite. Product modules (Playbooks, CRM, billing, Document
Vault, Channel Shield) stay first-class OS modules; they are not seams.
"""

from __future__ import annotations

from keprix.seams.bootstrap import ensure_default_seams, reset_seams_for_tests
from keprix.seams.consumers import (
    get_fs,
    get_llm,
    get_memory,
    get_shell,
    get_subagent,
    get_web,
)
from keprix.seams.definitions import (
    FsDefinition,
    LlmDefinition,
    MemoryDefinition,
    ShellDefinition,
    SubagentDefinition,
    WebDefinition,
)
from keprix.seams.errors import SeamError, SeamNotFoundError, SeamPolicyDenied
from keprix.seams.ids import SEAM_IDS, SeamId
from keprix.seams.registry import SeamRegistry, get_seam_registry

__all__ = [
    "SEAM_IDS",
    "FsDefinition",
    "LlmDefinition",
    "MemoryDefinition",
    "SeamError",
    "SeamId",
    "SeamNotFoundError",
    "SeamPolicyDenied",
    "SeamRegistry",
    "ShellDefinition",
    "SubagentDefinition",
    "WebDefinition",
    "ensure_default_seams",
    "get_fs",
    "get_llm",
    "get_memory",
    "get_seam_registry",
    "get_shell",
    "get_subagent",
    "get_web",
    "reset_seams_for_tests",
]
