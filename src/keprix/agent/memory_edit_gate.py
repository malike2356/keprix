"""Remember/forget confirmation gate (Prompt 295).

Blocks false confirmations when the user asked to remember or forget but the
memory tool was not called this turn.
"""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

MemoryEditIntent = Literal["remember", "forget"]

_REMEMBER_RE = re.compile(
    r"\b("
    r"remember\s+(?:that|this|to|my|i|we)|"
    r"please\s+remember|"
    r"don'?t\s+forget|"
    r"save\s+(?:this|that)\s+(?:to\s+)?(?:memory|preference)|"
    r"forget\s+(?:that|this|about|my)|"
    r"please\s+forget|"
    r"stop\s+remembering|"
    r"remove\s+(?:that|this)\s+from\s+(?:your\s+)?memory"
    r")\b",
    re.IGNORECASE,
)

_FORGET_RE = re.compile(
    r"\b(forget|stop\s+remembering|remove\s+from\s+(?:your\s+)?memory)\b",
    re.IGNORECASE,
)

_CONFIRM_RE = re.compile(
    r"\b("
    r"i(?:'ll| will)?\s+remember|"
    r"i(?:'ve| have)?\s+remembered|"
    r"got\s+it|"
    r"noted|"
    r"saved\s+(?:to\s+)?(?:memory|preferences?)|"
    r"i(?:'ll| will)?\s+forget|"
    r"i(?:'ve| have)?\s+forgotten|"
    r"removed\s+from\s+memory|"
    r"won'?t\s+remember"
    r")\b",
    re.IGNORECASE,
)

_CONTINUITY_REF_RE = re.compile(
    r"\b("
    r"my\s+project|"
    r"the\s+bug\s+we\s+discussed|"
    r"what\s+you\s+suggested|"
    r"as\s+we\s+(?:discussed|talked)|"
    r"last\s+time|"
    r"yesterday|"
    r"earlier\s+(?:today|this\s+week)|"
    r"in\s+our\s+(?:last|previous)\s+(?:chat|session|conversation)|"
    r"you\s+(?:told|said|suggested)\s+me"
    r")\b",
    re.IGNORECASE,
)

MEMORY_EDIT_NUDGE = (
    "You claimed to remember or forget something, but you did not call the "
    "memory tool this turn. Call memory with action=add, replace, or remove "
    "before confirming to the user."
)

CONTINUITY_SEARCH_NUDGE = (
    "The user referred to prior shared context that is not clearly in the "
    "visible messages. Call session_search, conversation_search, or "
    "recent_chats before asking them to repeat themselves."
)


def detect_memory_edit_intent(user_text: str) -> Optional[MemoryEditIntent]:
    text = (user_text or "").strip()
    if not text or not _REMEMBER_RE.search(text):
        return None
    if _FORGET_RE.search(text):
        return "forget"
    return "remember"


def looks_like_memory_confirmation(assistant_text: str) -> bool:
    return bool(_CONFIRM_RE.search(assistant_text or ""))


def has_continuity_reference(user_text: str) -> bool:
    return bool(_CONTINUITY_REF_RE.search(user_text or ""))


def memory_edit_called(agent: Any) -> bool:
    return bool(getattr(agent, "_memory_edited_this_turn", False))


def past_chat_search_called(agent: Any) -> bool:
    return bool(getattr(agent, "_past_chat_search_this_turn", False))


def evaluate_memory_edit_gate(
    user_text: str,
    assistant_text: str,
    agent: Any,
) -> Optional[str]:
    """Return a nudge message when a false remember/forget confirm is detected."""
    if getattr(agent, "_memory_edit_gate_retried", False):
        return None
    intent = detect_memory_edit_intent(user_text)
    if intent is None:
        return None
    if memory_edit_called(agent):
        return None
    if not looks_like_memory_confirmation(assistant_text):
        # Still block bare "OK" style confirms that imply compliance without
        # the tool when the user explicitly asked to remember/forget.
        lowered = (assistant_text or "").strip().lower()
        if not lowered:
            return None
        soft = any(
            token in lowered
            for token in ("ok", "okay", "sure", "done", "will do", "understood")
        )
        if not soft and len(lowered.split()) > 40:
            # Long answer without confirm verbs: allow (may be clarifying).
            return None
        if not soft and not looks_like_memory_confirmation(assistant_text):
            return None
    return MEMORY_EDIT_NUDGE


def evaluate_continuity_search_gate(
    user_text: str,
    assistant_text: str,
    agent: Any,
) -> Optional[str]:
    """Nudge once when continuity refs appear and no past-chat search ran."""
    if getattr(agent, "_continuity_search_gate_retried", False):
        return None
    if not has_continuity_reference(user_text):
        return None
    if past_chat_search_called(agent):
        return None
    # Only nudge when the assistant is asking the user to restate history.
    ask_again = re.search(
        r"\b(can you (remind|repeat|tell) me|what (was|were)|i don'?t (recall|remember)|"
        r"could you (clarify|provide) (more )?context)\b",
        assistant_text or "",
        re.IGNORECASE,
    )
    if not ask_again:
        return None
    return CONTINUITY_SEARCH_NUDGE


def mark_memory_edited(agent: Any) -> None:
    if agent is not None:
        agent._memory_edited_this_turn = True


def mark_past_chat_search(agent: Any) -> None:
    if agent is not None:
        agent._past_chat_search_this_turn = True


def reset_continuity_turn_flags(agent: Any) -> None:
    if agent is None:
        return
    agent._memory_edited_this_turn = False
    agent._past_chat_search_this_turn = False
    agent._memory_edit_gate_retried = False
    agent._continuity_search_gate_retried = False
