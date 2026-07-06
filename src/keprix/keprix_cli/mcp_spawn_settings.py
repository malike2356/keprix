"""Runtime settings for autonomous MCP spawn (env + config.yaml)."""

from __future__ import annotations

import os


def is_auto_mcp_spawn_enabled() -> bool:
    """True when auto-spawn is on via env or ``mcp.auto_spawn_enabled`` in config."""
    explicit = os.environ.get("KEPRIX_AUTO_MCP_SPAWN")
    if explicit is not None and str(explicit).strip() != "":
        return str(explicit).strip().lower() in ("1", "true", "yes", "on")
    try:
        from keprix_cli.config import load_config

        cfg = load_config()
        mcp_cfg = cfg.get("mcp") if isinstance(cfg.get("mcp"), dict) else {}
        return bool(mcp_cfg.get("auto_spawn_enabled", False))
    except Exception:
        return False


def set_auto_mcp_spawn_enabled(enabled: bool) -> bool:
    """Persist auto-spawn toggle in config.yaml and refresh tool availability cache."""
    from keprix_cli.config import load_config, save_config

    cfg = load_config()
    if "mcp" not in cfg or not isinstance(cfg.get("mcp"), dict):
        cfg["mcp"] = {}
    cfg["mcp"]["auto_spawn_enabled"] = bool(enabled)
    save_config(cfg)
    try:
        from tools.registry import invalidate_check_fn_cache

        invalidate_check_fn_cache()
    except Exception:
        pass
    return bool(enabled)
