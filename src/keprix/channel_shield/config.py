"""Channel Shield runtime config (home config.yaml + env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keprix.channel_shield.types import CHANNELS

DEFAULT_SANDBOX_EXTENSIONS = (
    "exe",
    "dll",
    "scr",
    "iso",
    "js",
    "vbs",
    "wsf",
    "hta",
    "lnk",
)


@dataclass
class ChannelShieldConfig:
    enabled: bool = False
    fail_closed_default: bool = True
    smtp_host: str = "0.0.0.0"
    smtp_port: int = 2525
    clamav_socket: str | None = None
    yara_rules_dir: str | None = None
    sandbox_required_for: list[str] = field(default_factory=lambda: list(DEFAULT_SANDBOX_EXTENSIONS))
    adapters: dict[str, bool] = field(
        default_factory=lambda: {c: True for c in CHANNELS}
    )
    scout_emit_signals: bool = True
    scout_honour_commands: bool = True
    auto_release_suspects: bool = False
    notify_targets: list[str] = field(default_factory=list)
    raw_store_dir: str = ""

    def adapter_enabled(self, channel: str) -> bool:
        return bool(self.adapters.get(channel, True))


_CONFIG: ChannelShieldConfig | None = None


def _home_config_path() -> Path:
    return Path(os.path.expanduser("~/.keprix/config.yaml"))


def _merge_section(data: dict[str, Any]) -> dict[str, Any]:
    """Prefer channel_shield; accept legacy email_shield alias."""
    primary = data.get("channel_shield")
    legacy = data.get("email_shield")
    if isinstance(primary, dict) and isinstance(legacy, dict):
        merged = {**legacy, **primary}
        return merged
    if isinstance(primary, dict):
        return primary
    if isinstance(legacy, dict):
        return legacy
    return {}


def _feature_flag_override() -> bool | None:
    """Return explicit Feature Manager override; defaults do not enable scanning."""
    try:
        from keprix.feature_flags.store import FeatureFlagStore

        overrides = FeatureFlagStore().load_overrides()
    except Exception:
        return None

    if "channel_shield" not in overrides:
        return None
    return bool(overrides["channel_shield"])


def load_channel_shield_config(*, force: bool = False) -> ChannelShieldConfig:
    global _CONFIG
    if _CONFIG is not None and not force:
        return _CONFIG

    section: dict[str, Any] = {}
    path = _home_config_path()
    if path.is_file():
        try:
            import yaml

            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(raw, dict):
                section = _merge_section(raw)
        except Exception:
            section = {}

    env_enabled = os.environ.get("CHANNEL_SHIELD_ENABLED", "").strip().lower()
    enabled = bool(section.get("enabled", False))
    flag_override = _feature_flag_override()
    if flag_override is not None:
        enabled = flag_override
    if env_enabled in {"1", "true", "yes", "on"}:
        enabled = True
    elif env_enabled in {"0", "false", "no", "off"}:
        enabled = False

    smtp = section.get("smtp") if isinstance(section.get("smtp"), dict) else {}
    adapters_raw = section.get("adapters") if isinstance(section.get("adapters"), dict) else {}
    adapters = {c: True for c in CHANNELS}
    for key, value in adapters_raw.items():
        if key in adapters:
            adapters[key] = bool(value)

    scout = section.get("scout") if isinstance(section.get("scout"), dict) else {}
    sandbox = section.get("sandbox_required_for")
    if not isinstance(sandbox, list):
        sandbox = list(DEFAULT_SANDBOX_EXTENSIONS)

    store_dir = str(section.get("raw_store_dir") or "").strip()
    if not store_dir:
        store_dir = str(Path(os.path.expanduser("~/.keprix/channel_shield/raw")))

    _CONFIG = ChannelShieldConfig(
        enabled=enabled,
        fail_closed_default=bool(section.get("fail_closed_default", True)),
        smtp_host=str(smtp.get("host") or os.environ.get("CHANNEL_SHIELD_SMTP_HOST") or "0.0.0.0"),
        smtp_port=int(smtp.get("port") or os.environ.get("CHANNEL_SHIELD_SMTP_PORT") or 2525),
        clamav_socket=(
            str(section["clamav_socket"])
            if section.get("clamav_socket")
            else (os.environ.get("CHANNEL_SHIELD_CLAMAV_SOCKET") or None)
        ),
        yara_rules_dir=(
            str(section["yara_rules_dir"])
            if section.get("yara_rules_dir")
            else (os.environ.get("CHANNEL_SHIELD_YARA_RULES_DIR") or None)
        ),
        sandbox_required_for=[str(x).lower().lstrip(".") for x in sandbox],
        adapters=adapters,
        scout_emit_signals=bool(scout.get("emit_signals", True)),
        scout_honour_commands=bool(scout.get("honour_commands", True)),
        auto_release_suspects=bool(section.get("auto_release_suspects", False)),
        notify_targets=list(section.get("notify_targets") or []),
        raw_store_dir=store_dir,
    )
    return _CONFIG


def reset_channel_shield_config() -> None:
    global _CONFIG
    _CONFIG = None


def config_to_dict(cfg: ChannelShieldConfig | None = None) -> dict[str, Any]:
    cfg = cfg or load_channel_shield_config()
    return {
        "enabled": cfg.enabled,
        "fail_closed_default": cfg.fail_closed_default,
        "smtp": {"host": cfg.smtp_host, "port": cfg.smtp_port},
        "clamav_socket": cfg.clamav_socket,
        "yara_rules_dir": cfg.yara_rules_dir,
        "sandbox_required_for": list(cfg.sandbox_required_for),
        "adapters": dict(cfg.adapters),
        "scout": {
            "emit_signals": cfg.scout_emit_signals,
            "honour_commands": cfg.scout_honour_commands,
        },
        "auto_release_suspects": cfg.auto_release_suspects,
        "notify_targets": list(cfg.notify_targets),
        "raw_store_dir": cfg.raw_store_dir,
    }
