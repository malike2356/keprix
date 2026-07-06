"""Runtime LLM provider routing with demotion support for auto-repair."""

from __future__ import annotations

import copy
from typing import Any


class LLMRouter:
    _instance: LLMRouter | None = None

    def __init__(self) -> None:
        self._last_demotion: str | None = None
        self._primary_provider: str | None = None

    @classmethod
    def get_instance(cls) -> LLMRouter:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def current_primary(self) -> str:
        if self._primary_provider:
            return self._primary_provider
        try:
            from keprix_cli.config import load_config

            cfg = load_config()
            model = cfg.get("model") or {}
            if isinstance(model, dict):
                return str(model.get("provider") or "unknown")
        except Exception:
            pass
        return self._last_demotion or "unknown"

    def demote_provider(self, provider_name: str, reason: str = "") -> None:
        """Move a failing provider down the fallback chain and switch primary if needed."""
        from keprix_cli.config import load_config, save_config
        from keprix_cli.fallback_config import get_fallback_chain

        normalized = provider_name.strip().lower()
        cfg = copy.deepcopy(load_config())
        chain = get_fallback_chain(cfg)

        demoted_entry: dict[str, Any] | None = None
        remaining: list[dict[str, Any]] = []
        for entry in chain:
            entry_provider = str(entry.get("provider") or "").strip().lower()
            if entry_provider == normalized and demoted_entry is None:
                demoted_entry = dict(entry)
            else:
                remaining.append(dict(entry))

        if demoted_entry is not None:
            remaining.append(demoted_entry)
            cfg["fallback_providers"] = remaining
        elif chain:
            cfg["fallback_providers"] = remaining

        model = cfg.setdefault("model", {})
        if isinstance(model, dict):
            current = str(model.get("provider") or "").strip().lower()
            if current == normalized and remaining:
                model["provider"] = remaining[0]["provider"]
                model["name"] = remaining[0].get("model", model.get("name"))

        save_config(cfg)
        self._last_demotion = normalized
        model = cfg.get("model") or {}
        if isinstance(model, dict) and model.get("provider"):
            self._primary_provider = str(model["provider"])
