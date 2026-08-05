"""Shared first-run setup status probes for CLI, TUI, and web."""

from __future__ import annotations

import json
import os
from typing import Any

DOCS_FIRST_RUN_URL = "https://keprix.nousresearch.com/docs/getting-started/first-run"

WIZARD_SECTIONS = ("model", "tts", "terminal", "gateway", "tools", "agent")


def provider_configured() -> bool:
    """Return True when at least one inference provider is usable."""
    from keprix_cli.config import DEFAULT_CONFIG, get_env_path, get_keprix_home, load_config
    from keprix_cli.auth import PROVIDER_REGISTRY, get_auth_status

    _DEFAULT_MODEL = DEFAULT_CONFIG.get("model", "")
    cfg = load_config()
    model_cfg = cfg.get("model")
    if isinstance(model_cfg, dict):
        _model_name = (model_cfg.get("default") or "").strip()
    elif isinstance(model_cfg, str):
        _model_name = model_cfg.strip()
    else:
        _model_name = ""
    _has_keprix_config = _model_name and _model_name != _DEFAULT_MODEL

    provider_env_vars = {
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_TOKEN",
        "OPENAI_BASE_URL",
    }
    for pconfig in PROVIDER_REGISTRY.values():
        if pconfig.auth_type == "api_key":
            provider_env_vars.update(pconfig.api_key_env_vars)
    if any(os.getenv(v) for v in provider_env_vars):
        return True

    env_file = get_env_path()
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                val = val.strip().strip("'\"")
                if key.strip() in provider_env_vars and val:
                    return True
        except Exception:
            pass

    try:
        for provider_id, pconfig in PROVIDER_REGISTRY.items():
            if pconfig.auth_type != "api_key":
                continue
            status = get_auth_status(provider_id)
            if status.get("logged_in"):
                return True
    except Exception:
        pass

    auth_file = get_keprix_home() / "auth.json"
    if auth_file.exists():
        try:
            auth = json.loads(auth_file.read_text())
            active = auth.get("active_provider")
            if active:
                status = get_auth_status(active)
                if status.get("logged_in"):
                    return True
        except Exception:
            pass

    if isinstance(model_cfg, dict):
        cfg_provider = (model_cfg.get("provider") or "").strip()
        cfg_base_url = (model_cfg.get("base_url") or "").strip()
        cfg_api_key = (model_cfg.get("api_key") or "").strip()
        if cfg_provider or cfg_base_url or cfg_api_key:
            return True

    if _has_keprix_config:
        try:
            from agent.anthropic_adapter import (
                is_claude_code_token_valid,
                read_claude_code_credentials,
            )

            creds = read_claude_code_credentials()
            if creds and (
                is_claude_code_token_valid(creds) or creds.get("refreshToken")
            ):
                return True
        except Exception:
            pass

    return False


def channel_configured() -> bool:
    """Return True when at least one messaging channel credential is present."""
    channel_env = (
        "TELEGRAM_BOT_TOKEN",
        "DISCORD_BOT_TOKEN",
        "SLACK_BOT_TOKEN",
        "KEPRIX_TELEGRAM_BOT_TOKEN",
        "KEPRIX_DISCORD_BOT_TOKEN",
        "EMAIL_ADDRESS",
        "WHATSAPP_ENABLED",
        "WHATSAPP_CLOUD_ACCESS_TOKEN",
        "SIGNAL_HTTP_URL",
        "MATRIX_ACCESS_TOKEN",
        "TWILIO_ACCOUNT_SID",
    )
    if any(os.getenv(name) for name in channel_env):
        return True
    try:
        from keprix.channels.channel_config_store import list_configurations

        if any(row.get("configured") for row in list_configurations()):
            return True
    except Exception:
        pass
    try:
        from keprix_cli.config import get_keprix_home

        gateway = get_keprix_home() / "gateway.json"
        if gateway.is_file():
            data = json.loads(gateway.read_text(encoding="utf-8"))
            platforms = data.get("platforms") or data.get("channels") or {}
            if isinstance(platforms, dict) and any(platforms.values()):
                return True
    except Exception:
        pass
    return False


def model_configured() -> bool:
    """Return True when a non-default model is selected in config."""
    from keprix_cli.config import DEFAULT_CONFIG, load_config

    cfg = load_config()
    model_cfg = cfg.get("model")
    default_model = DEFAULT_CONFIG.get("model", "")
    if isinstance(model_cfg, dict):
        name = (model_cfg.get("default") or "").strip()
        provider = (model_cfg.get("provider") or "").strip()
        return bool(name and name != default_model) or bool(provider)
    if isinstance(model_cfg, str):
        name = model_cfg.strip()
        return bool(name and name != default_model)
    return False


def setup_status_snapshot() -> dict[str, Any]:
    """JSON-safe setup snapshot for TUI and web consumers."""
    active_provider = None
    default_model = None
    try:
        from keprix_cli.auth import get_active_provider
        from keprix_cli.config import load_config

        active_provider = get_active_provider()
        cfg = load_config()
        model_cfg = cfg.get("model")
        if isinstance(model_cfg, dict):
            default_model = (model_cfg.get("default") or "").strip() or None
            if not active_provider:
                active_provider = (model_cfg.get("provider") or "").strip() or None
        elif isinstance(model_cfg, str) and model_cfg.strip():
            default_model = model_cfg.strip()
    except Exception:
        pass

    configured = provider_configured()
    return {
        "provider_configured": configured,
        "model_configured": model_configured() if configured else False,
        "active_provider": active_provider,
        "default_model": default_model,
        "wizard_sections": list(WIZARD_SECTIONS),
        "docs_url": DOCS_FIRST_RUN_URL,
    }
