"""Escalation config (K05)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


DEFAULT_HOLDING = "Let me look into that for you. I'll be right back."


@dataclass
class EscalationConfig:
    confidence_threshold: float = 0.7
    holding_message_template: str = DEFAULT_HOLDING
    notify_channels: list[str] = field(default_factory=lambda: ["telegram", "dashboard"])
    timeout_minutes: int = 30
    enabled: bool = True
    telegram_chat_id: str | None = None
    notify_email: str | None = None
    notify_webhook_url: str | None = None


def load_escalation_config(overrides: dict | None = None) -> EscalationConfig:
    cfg = EscalationConfig(
        confidence_threshold=float(os.getenv("AIVA_ESCALATION_CONFIDENCE_THRESHOLD", "0.7")),
        holding_message_template=os.getenv("AIVA_ESCALATION_HOLDING_MESSAGE", DEFAULT_HOLDING),
        timeout_minutes=int(os.getenv("AIVA_ESCALATION_TIMEOUT_MINUTES", "30")),
        enabled=os.getenv("AIVA_ESCALATION_ENABLED", "1") not in ("0", "false", "False"),
        telegram_chat_id=os.getenv("AIVA_ESCALATION_TELEGRAM_CHAT_ID") or None,
        notify_email=os.getenv("AIVA_ESCALATION_NOTIFY_EMAIL") or None,
        notify_webhook_url=os.getenv("AIVA_ESCALATION_WEBHOOK_URL") or None,
    )
    channels = os.getenv("AIVA_ESCALATION_NOTIFY_CHANNELS")
    if channels:
        cfg.notify_channels = [c.strip() for c in channels.split(",") if c.strip()]
    if overrides:
        for key, value in overrides.items():
            if hasattr(cfg, key) and value is not None:
                setattr(cfg, key, value)
    return cfg
