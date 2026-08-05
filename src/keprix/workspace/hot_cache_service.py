"""Rolling wiki/hot.md cache for workspace orientation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.workspace.hot_cache_config import HotCacheConfig, load_hot_cache_config, save_hot_cache_config
from keprix.workspace.template_presets import workspace_root


def _root(workspace_id: str, workspace_path: str | None = None) -> Path:
    return Path(workspace_path).expanduser().resolve() if workspace_path else workspace_root(workspace_id)


def _cap_words(text: str, max_words: int = 560) -> str:
    words = text.split()
    return " ".join(words[:max_words])


class HotCacheService:
    def get_config(self, workspace_id: str, workspace_path: str | None = None) -> HotCacheConfig:
        return load_hot_cache_config(_root(workspace_id, workspace_path))

    def set_config(self, workspace_id: str, enabled: bool, workspace_path: str | None = None) -> HotCacheConfig:
        root = _root(workspace_id, workspace_path)
        root.mkdir(parents=True, exist_ok=True)
        return save_hot_cache_config(root, HotCacheConfig(enabled=enabled))

    def read(self, workspace_id: str, workspace_path: str | None = None) -> dict[str, Any]:
        root = _root(workspace_id, workspace_path)
        path = root / "wiki" / "hot.md"
        config = self.get_config(workspace_id, workspace_path)
        return {"enabled": config.enabled, "path": str(path), "content": path.read_text(encoding="utf-8") if path.is_file() else ""}

    def refresh(
        self,
        workspace_id: str,
        *,
        workspace_path: str | None = None,
        source_session_id: str | None = None,
        recent_text: str = "",
        summary: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        root = _root(workspace_id, workspace_path)
        config = self.get_config(workspace_id, workspace_path)
        path = root / "wiki" / "hot.md"
        if not config.enabled and not force:
            return {"enabled": False, "path": str(path), "written": False, "content": path.read_text(encoding="utf-8") if path.is_file() else ""}
        content = self._render(source_session_id=source_session_id, recent_text=recent_text, summary=summary)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"enabled": config.enabled, "path": str(path), "written": True, "content": content}

    def _render(self, *, source_session_id: str | None, recent_text: str, summary: str | None) -> str:
        body = _cap_words(summary or self._heuristic_summary(recent_text))
        updated = datetime.now(timezone.utc).isoformat()
        return (
            "# Hot cache\n\n"
            "> Rolling context (~500 tokens). Auto-updated. Do not manually edit unless correcting errors.\n\n"
            f"**Last updated:** {updated}\n"
            f"**Source session:** {source_session_id or 'manual'}\n\n"
            "## Recent focus\n"
            f"- {body or 'No recent focus captured yet.'}\n\n"
            "## Open threads\n"
            "- Review unresolved actions from the latest session.\n"
        )

    def _heuristic_summary(self, text: str) -> str:
        lines = [line.strip("-* \t") for line in text.splitlines() if line.strip()]
        if not lines:
            return ""
        return "; ".join(lines[:8])
