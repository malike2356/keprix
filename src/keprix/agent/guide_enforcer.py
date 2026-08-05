"""Ensure persona AGENT_GUIDE.md is read before acting (OpenMontage pattern)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)

GUIDE_FILENAME = "AGENT_GUIDE.md"
READ_TOOLS = frozenset(
    {
        "read_file",
        "skill_view",
        "view_file",
        "open_file",
        "cat",
    }
)


def skills_personas_root() -> Path:
    return Path(__file__).resolve().parents[1] / "skills" / "personas"


def resolve_guide_path(persona: str) -> Path:
    key = (persona or "nexus").strip().lower() or "nexus"
    return skills_personas_root() / key / GUIDE_FILENAME


def guide_relative_path(persona: str) -> str:
    key = (persona or "nexus").strip().lower() or "nexus"
    return f"skills/personas/{key}/{GUIDE_FILENAME}"


def mandatory_guide_instruction(persona: str) -> str:
    rel = guide_relative_path(persona)
    return (
        f"**MANDATORY: Read {rel} before responding to ANY user message.** "
        "Do not act on the user's request until you have read the routing guide. "
        "It contains the decision tree that determines your first action. "
        "Skipping it WILL cause you to route to the wrong persona."
    )


def load_guide_content(persona: str) -> str:
    path = resolve_guide_path(persona)
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.debug("guide load failed for %s: %s", persona, exc)
        return ""


def path_looks_like_guide(path_text: str, persona: str) -> bool:
    text = (path_text or "").replace("\\", "/").lower()
    if not text:
        return False
    key = (persona or "nexus").strip().lower()
    if GUIDE_FILENAME.lower() in text and (key in text or "personas" in text):
        return True
    return text.endswith(f"/{key}/{GUIDE_FILENAME.lower()}") or text.endswith(
        GUIDE_FILENAME.lower()
    )


@dataclass
class GuideEnforcer:
    """Ensures the agent reads its AGENT_GUIDE.md before acting."""

    persona: str = "nexus"
    guide_read: bool = False
    guide_injected: bool = False
    warned: bool = False
    _tool_calls: int = 0

    @property
    def guide_path(self) -> Path:
        return resolve_guide_path(self.persona)

    def read_guide_text(self) -> str:
        return load_guide_content(self.persona)

    def injection_message(self) -> str:
        content = self.read_guide_text()
        if not content:
            return mandatory_guide_instruction(self.persona)
        return (
            "You must read and follow this routing guide:\n\n"
            f"{content.strip()}"
        )

    def ensure_injected(self, agent: Any = None) -> Optional[str]:
        """Inject guide content once per session if not yet read."""
        if self.guide_read or self.guide_injected:
            return None
        message = self.injection_message()
        self.guide_injected = True
        if agent is not None:
            existing = getattr(agent, "ephemeral_system_prompt", None) or ""
            if "routing guide" not in existing.lower() and "AGENT_GUIDE" not in existing:
                agent.ephemeral_system_prompt = (
                    f"{message}\n\n{existing}".strip() if existing else message
                )
            agent._guide_enforcer = self
        return message

    def record_tool(self, tool_name: str, args: Mapping[str, Any] | None = None) -> None:
        args = args or {}
        self._tool_calls += 1
        if tool_name in READ_TOOLS:
            hay = " ".join(
                str(args.get(key) or "")
                for key in ("path", "file_path", "filename", "name", "target", "query")
            )
            if path_looks_like_guide(hay, self.persona):
                self.guide_read = True

    def before_tool(
        self,
        tool_name: str,
        args: Mapping[str, Any] | None = None,
    ) -> Optional[str]:
        """Warn on first non-guide tool if the guide was never read."""
        args = args or {}
        if self.guide_read:
            return None
        if tool_name in READ_TOOLS and path_looks_like_guide(
            " ".join(str(args.get(k) or "") for k in ("path", "file_path", "filename", "name")),
            self.persona,
        ):
            return None
        if self._tool_calls == 0 and not self.warned:
            self.warned = True
            self.ensure_injected()
            return (
                "guide_enforcer: read AGENT_GUIDE.md before other tools. "
                f"Required path: {guide_relative_path(self.persona)}. "
                "Guide content has been injected into the session."
            )
        return None

    def check_routing_mismatch(
        self,
        user_message: str,
        chosen_persona: str,
        *,
        workspace_id: str = "default",
    ) -> Optional[str]:
        """Catch obvious wrong-persona routes using the NEXUS keyword router."""
        chosen = (chosen_persona or "").strip().upper()
        if not chosen or chosen in {"NEXUS", "DEFAULT", ""}:
            return None
        try:
            from keprix.personas.nexus.orchestrator import NexusOrchestrator

            decision = NexusOrchestrator(workspace_id=workspace_id, run_id="guide").route(
                user_message
            )
        except Exception:
            return None
        expected = decision.primary_agent
        if expected == chosen:
            return None
        if decision.handled_by_nexus:
            return None
        # Only flag high-confidence mismatches (security -> FORGE, etc.).
        if expected == "WARDEN" and chosen == "FORGE":
            return (
                "guide_enforcer: security/compliance request should route to WARDEN, "
                f"not {chosen}."
            )
        if expected == "CODEX" and chosen in {"FORGE", "BEACON"}:
            return (
                f"guide_enforcer: legal/contract request should route to CODEX, not {chosen}."
            )
        if expected == "ECHO" and chosen in {"COMPASS", "SAGE"}:
            return (
                f"guide_enforcer: reception/scheduling request should route to ECHO, not {chosen}."
            )
        if decision.confidence >= 0.8 and expected != chosen:
            return (
                f"guide_enforcer: request looks like {expected}, but route chose {chosen}."
            )
        return None


def get_or_create_guide_enforcer(agent: Any, persona: str | None = None) -> GuideEnforcer:
    existing = getattr(agent, "_guide_enforcer", None)
    if isinstance(existing, GuideEnforcer):
        if persona and existing.persona != persona.strip().lower():
            existing.persona = persona.strip().lower()
        return existing
    key = (persona or getattr(agent, "_active_persona", None) or "nexus")
    if isinstance(key, str):
        key = key.strip().lower() or "nexus"
    else:
        key = "nexus"
    enforcer = GuideEnforcer(persona=key)
    agent._guide_enforcer = enforcer
    return enforcer


def apply_guide_enforcer_gate(
    agent: Any,
    tool_name: str,
    args: dict[str, Any] | None = None,
) -> Optional[str]:
    """Executor hook: soft-block first tool if guide unread."""
    if not bool(getattr(agent, "_guide_enforce", True)):
        return None
    persona = getattr(agent, "_active_persona", None) or "nexus"
    enforcer = get_or_create_guide_enforcer(agent, str(persona))
    warning = enforcer.before_tool(tool_name, args)
    enforcer.record_tool(tool_name, args)
    return warning


__all__ = [
    "GuideEnforcer",
    "apply_guide_enforcer_gate",
    "get_or_create_guide_enforcer",
    "guide_relative_path",
    "load_guide_content",
    "mandatory_guide_instruction",
    "resolve_guide_path",
]
