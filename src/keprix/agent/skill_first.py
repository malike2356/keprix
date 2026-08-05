"""Skill-first execution gate (Prompt 292).

Before file create, code execution, terminal, or computer_use, require that
plausibly relevant SKILL.md files were viewed via ``skill_view`` in this
session (with optional TTL). Soft conversational tools are never gated.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

logger = logging.getLogger(__name__)

GATED_TOOLS = frozenset(
    {
        "write_file",
        "patch",
        "terminal",
        "execute_code",
        "computer_use",
        "create_file",
        "str_replace",
        "bash",
        "run_terminal_cmd",
    }
)

VIEW_TOOLS = frozenset({"skill_view"})

# Extension / keyword hints -> skill name tokens to prefer when matching.
_EXT_HINTS: dict[str, tuple[str, ...]] = {
    ".pptx": ("pptx", "powerpoint", "slides", "presentation"),
    ".ppt": ("pptx", "powerpoint", "slides", "presentation"),
    ".docx": ("docx", "word", "document"),
    ".doc": ("docx", "word", "document"),
    ".pdf": ("pdf",),
    ".xlsx": ("xlsx", "spreadsheet", "excel", "csv"),
    ".xls": ("xlsx", "spreadsheet", "excel"),
    ".csv": ("xlsx", "spreadsheet", "csv", "data-analysis", "data_analysis"),
    ".jsx": ("frontend", "frontend-design", "react"),
    ".tsx": ("frontend", "frontend-design", "react"),
    ".html": ("frontend", "frontend-design", "html"),
    ".css": ("frontend", "frontend-design"),
}

_DEFAULT_VIEW_TTL_SECONDS = 6 * 60 * 60  # session-friendly cache


class SkillFirstAction(str, Enum):
    ALLOW = "allow"
    REQUIRE_SKILL_READ = "require_skill_read"
    BYPASS = "bypass"


@dataclass(frozen=True)
class SkillFirstDecision:
    action: SkillFirstAction
    message: str = ""
    required_skills: tuple[str, ...] = ()
    matched_skills: tuple[str, ...] = ()
    profile: str = "standard"
    reason: str = ""

    @property
    def allows_execution(self) -> bool:
        return self.action in (SkillFirstAction.ALLOW, SkillFirstAction.BYPASS)


@dataclass
class _ViewRecord:
    viewed_at: float


@dataclass
class SkillFirstGate:
    """Require skill_view before gated mutating / computer tools."""

    profile: str = "standard"
    enabled: bool = True
    view_ttl_seconds: float = _DEFAULT_VIEW_TTL_SECONDS
    skill_catalog: Sequence[Mapping[str, Any]] | None = None
    _viewed: dict[str, _ViewRecord] = field(default_factory=dict)
    _warned_once: set[str] = field(default_factory=set)

    def record_skill_view(self, name: str) -> None:
        key = _normalize_skill_name(name)
        if not key:
            return
        self._viewed[key] = _ViewRecord(viewed_at=time.time())

    def before_tool(
        self,
        tool_name: str,
        args: Mapping[str, Any] | None = None,
        *,
        task_hint: str = "",
    ) -> SkillFirstDecision:
        args = args or {}
        profile = (self.profile or "standard").strip().lower() or "standard"

        if not self.enabled:
            return SkillFirstDecision(
                action=SkillFirstAction.BYPASS,
                profile=profile,
                reason="skill_first_disabled",
            )

        if tool_name in VIEW_TOOLS:
            name = str(args.get("name") or "")
            # Recording happens after successful execution in the executor.
            return SkillFirstDecision(action=SkillFirstAction.ALLOW, profile=profile)

        if tool_name not in GATED_TOOLS:
            return SkillFirstDecision(action=SkillFirstAction.ALLOW, profile=profile)

        matches = self.match_skills(tool_name, args, task_hint=task_hint)
        if not matches:
            return SkillFirstDecision(action=SkillFirstAction.ALLOW, profile=profile)

        unread = [name for name in matches if not self._was_viewed(name)]
        if not unread:
            self._emit_audit("skill_first.satisfied", tool_name, matches, profile)
            return SkillFirstDecision(
                action=SkillFirstAction.ALLOW,
                matched_skills=tuple(matches),
                profile=profile,
                reason="skills_viewed",
            )

        # Permissive: warn once per skill set, then allow.
        if profile in {"permissive", "low"}:
            warn_key = "|".join(sorted(unread))
            if warn_key not in self._warned_once:
                self._warned_once.add(warn_key)
                self._emit_audit(
                    "skill_first.bypassed",
                    tool_name,
                    unread,
                    profile,
                    extra={"mode": "warn_once"},
                )
                return SkillFirstDecision(
                    action=SkillFirstAction.BYPASS,
                    message=self._block_message(unread),
                    required_skills=tuple(unread),
                    matched_skills=tuple(matches),
                    profile=profile,
                    reason="permissive_warn_once",
                )
            self._emit_audit(
                "skill_first.bypassed",
                tool_name,
                unread,
                profile,
                extra={"mode": "already_warned"},
            )
            return SkillFirstDecision(
                action=SkillFirstAction.BYPASS,
                required_skills=tuple(unread),
                matched_skills=tuple(matches),
                profile=profile,
                reason="permissive_already_warned",
            )

        self._emit_audit("skill_first.required", tool_name, unread, profile)
        return SkillFirstDecision(
            action=SkillFirstAction.REQUIRE_SKILL_READ,
            message=self._block_message(unread),
            required_skills=tuple(unread),
            matched_skills=tuple(matches),
            profile=profile,
            reason="unread_skills",
        )

    def match_skills(
        self,
        tool_name: str,
        args: Mapping[str, Any],
        *,
        task_hint: str = "",
    ) -> list[str]:
        catalog = list(self.skill_catalog) if self.skill_catalog is not None else self._load_catalog()
        if not catalog:
            return []

        haystack = _build_haystack(tool_name, args, task_hint)
        if not haystack:
            return []

        scored: list[tuple[int, str]] = []
        for skill in catalog:
            name = str(skill.get("name") or "").strip()
            if not name:
                continue
            score = _score_skill(skill, haystack)
            if score > 0:
                scored.append((score, name))

        scored.sort(key=lambda item: (-item[0], item[1].lower()))
        # Cap to avoid forcing dozens of reads for vague terminal commands.
        return [name for _, name in scored[:5]]

    def _was_viewed(self, name: str) -> bool:
        key = _normalize_skill_name(name)
        record = self._viewed.get(key)
        if record is None:
            # Also accept qualified forms ending with :name
            for viewed_key, viewed_rec in self._viewed.items():
                if viewed_key == key or viewed_key.endswith(":" + key) or key.endswith(":" + viewed_key):
                    record = viewed_rec
                    break
        if record is None:
            return False
        if self.view_ttl_seconds <= 0:
            return True
        return (time.time() - record.viewed_at) <= self.view_ttl_seconds

    def _load_catalog(self) -> list[dict[str, Any]]:
        try:
            from tools.skills_tool import _find_all_skills

            return list(_find_all_skills(skip_disabled=False) or [])
        except Exception as exc:
            logger.debug("skill_first catalog load failed: %s", exc)
            return []

    @staticmethod
    def _block_message(unread: Sequence[str]) -> str:
        calls = ", ".join(f'skill_view(name="{name}")' for name in unread)
        return (
            "skill_first: view relevant SKILL.md before this tool. "
            f"Required: {calls}. "
            "Skipping skill reads lowers output quality; this is a defect, not an optimization."
        )

    @staticmethod
    def _emit_audit(
        event: str,
        tool_name: str,
        skills: Sequence[str],
        profile: str,
        *,
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        payload = {
            "event": event,
            "tool": tool_name,
            "skills": list(skills),
            "profile": profile,
        }
        if extra:
            payload.update(dict(extra))
        logger.info("skill_first audit %s", json.dumps(payload, ensure_ascii=False))
        try:
            from keprix.security.scout_integration import emit_scout_signal
            from keprix.security.scout_types import SignalCategory, SignalSeverity

            severity = (
                SignalSeverity.WARNING
                if event == "skill_first.required"
                else SignalSeverity.INFO
            )
            emit_scout_signal(
                SignalCategory.GOVERNANCE,
                severity,
                event,
                f"tool:{tool_name}",
                payload,
            )
        except Exception:
            pass


def resolve_skill_first_profile(agent: Any = None) -> str:
    """Resolve skill-first profile from operator policy kernel (Prompt 297)."""
    if agent is not None:
        # Prefer operator-policy-derived skill_first mapping when stamped.
        op = getattr(agent, "_operator_policy", None)
        if op is not None and hasattr(op, "skill_first_profile"):
            return str(op.skill_first_profile)
        explicit = getattr(agent, "_skill_first_profile", None)
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip().lower()
        cfg = getattr(agent, "_skill_first_config", None)
        if isinstance(cfg, Mapping):
            profile = cfg.get("profile")
            if isinstance(profile, str) and profile.strip():
                return profile.strip().lower()

    try:
        from keprix.security.operator_policy import get_operator_policy

        return get_operator_policy(agent=agent).skill_first_profile
    except Exception:
        pass
    return "standard"


def get_or_create_gate(agent: Any) -> SkillFirstGate | None:
    """Return the agent's SkillFirstGate, creating it when skill_first is enabled."""
    if agent is None:
        return None
    if not bool(getattr(agent, "_skill_first", True)):
        return None
    gate = getattr(agent, "_skill_first_gate", None)
    if isinstance(gate, SkillFirstGate):
        gate.profile = resolve_skill_first_profile(agent)
        gate.enabled = True
        return gate

    cfg = getattr(agent, "_skill_first_config", None)
    ttl = _DEFAULT_VIEW_TTL_SECONDS
    if isinstance(cfg, Mapping):
        try:
            ttl = float(cfg.get("view_ttl_seconds", ttl))
        except (TypeError, ValueError):
            ttl = _DEFAULT_VIEW_TTL_SECONDS

    gate = SkillFirstGate(
        profile=resolve_skill_first_profile(agent),
        enabled=True,
        view_ttl_seconds=ttl,
    )
    agent._skill_first_gate = gate
    return gate


def apply_skill_first_gate(
    agent: Any,
    tool_name: str,
    args: Mapping[str, Any] | None = None,
) -> str | None:
    """
    Executor hook.

    Returns a JSON error string when the tool must be blocked, else None.
    On successful skill_view, records the view (caller should only call after
    success; this helper also records optimistically when name is present and
    the tool is skill_view; prefer record_after_skill_view for accuracy).
    """
    gate = get_or_create_gate(agent)
    if gate is None:
        return None

    decision = gate.before_tool(tool_name, args or {})
    if decision.allows_execution:
        return None
    return json.dumps(
        {
            "error": decision.message,
            "skill_first": True,
            "required_skills": list(decision.required_skills),
            "profile": decision.profile,
        },
        ensure_ascii=False,
    )


def record_after_skill_view(agent: Any, tool_name: str, args: Mapping[str, Any], result: Any) -> None:
    """Record a successful skill_view on the agent's gate."""
    if tool_name not in VIEW_TOOLS:
        return
    gate = get_or_create_gate(agent)
    if gate is None:
        return
    name = str((args or {}).get("name") or "")
    resolved = _resolved_name_from_result(result) or name
    if not resolved:
        return
    if _skill_view_succeeded(result):
        gate.record_skill_view(resolved)


def skill_first_block_result(decision_or_json: SkillFirstDecision | str) -> str:
    if isinstance(decision_or_json, str):
        return decision_or_json
    return json.dumps(
        {
            "error": decision_or_json.message,
            "skill_first": True,
            "required_skills": list(decision_or_json.required_skills),
            "profile": decision_or_json.profile,
        },
        ensure_ascii=False,
    )


def _normalize_skill_name(name: str) -> str:
    return (name or "").strip().lower()


def _build_haystack(tool_name: str, args: Mapping[str, Any], task_hint: str) -> str:
    parts: list[str] = [tool_name, task_hint or ""]
    for key in ("path", "file_path", "filename", "command", "code", "content", "query", "prompt"):
        value = args.get(key)
        if value is not None:
            parts.append(str(value))
    # Include any stringish arg values for broader matching.
    for value in args.values():
        if isinstance(value, str) and value not in parts:
            parts.append(value)
    text = " ".join(parts).lower()
    # Expand extension hints into searchable tokens.
    for ext, tokens in _EXT_HINTS.items():
        if ext in text:
            text += " " + " ".join(tokens)
    return text


def _score_skill(skill: Mapping[str, Any], haystack: str) -> int:
    name = str(skill.get("name") or "").strip().lower()
    description = str(skill.get("description") or "").strip().lower()
    category = str(skill.get("category") or "").strip().lower()
    triggers = skill.get("triggers") or skill.get("keywords") or []
    if isinstance(triggers, str):
        trigger_tokens = [triggers.lower()]
    else:
        trigger_tokens = [str(t).lower() for t in triggers if t]

    score = 0
    name_tokens = _tokenize(name.replace("-", " ").replace("_", " "))
    for token in name_tokens:
        if len(token) >= 3 and token in haystack:
            score += 3
    if name and name in haystack:
        score += 5
    for token in trigger_tokens:
        if token and token in haystack:
            score += 4
    for token in _tokenize(description):
        if len(token) >= 5 and token in haystack:
            score += 1
    if category and category in haystack:
        score += 2

    # Strong path-extension matches against known skill families.
    for ext, hints in _EXT_HINTS.items():
        if ext in haystack and any(h in name or h in description for h in hints):
            score += 6
    return score


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _skill_view_succeeded(result: Any) -> bool:
    if result is None:
        return False
    if isinstance(result, dict):
        return bool(result.get("success"))
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except Exception:
            return "success" in result and "false" not in result[:40].lower()
        if isinstance(parsed, dict):
            return bool(parsed.get("success"))
    return False


def _resolved_name_from_result(result: Any) -> str:
    payload: Any = result
    if isinstance(result, str):
        try:
            payload = json.loads(result)
        except Exception:
            return ""
    if isinstance(payload, dict):
        return str(payload.get("name") or "")
    return ""
