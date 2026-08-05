"""Adapter registry for Channel Shield."""

from __future__ import annotations

from keprix.channel_shield.adapters.base import ChannelAdapter
from keprix.channel_shield.adapters.discord import DiscordAdapter
from keprix.channel_shield.adapters.email import EmailAdapter
from keprix.channel_shield.adapters.slack import SlackAdapter
from keprix.channel_shield.adapters.sms import SmsAdapter
from keprix.channel_shield.adapters.teams import TeamsAdapter
from keprix.channel_shield.adapters.telegram import TelegramAdapter
from keprix.channel_shield.adapters.web import WebAdapter
from keprix.channel_shield.adapters.whatsapp import WhatsAppAdapter
from keprix.channel_shield.types import CHANNELS

_ADAPTERS: dict[str, ChannelAdapter] | None = None


def _build() -> dict[str, ChannelAdapter]:
    instances: list[ChannelAdapter] = [
        EmailAdapter(),
        SlackAdapter(),
        TeamsAdapter(),
        TelegramAdapter(),
        WhatsAppAdapter(),
        DiscordAdapter(),
        SmsAdapter(),
        WebAdapter(),
    ]
    return {a.channel: a for a in instances}


def get_adapter(channel: str) -> ChannelAdapter:
    global _ADAPTERS
    if _ADAPTERS is None:
        _ADAPTERS = _build()
    adapter = _ADAPTERS.get(channel)
    if adapter is None:
        raise KeyError(f"unknown channel adapter: {channel}")
    return adapter


def list_adapters() -> list[str]:
    return list(CHANNELS)


async def adapters_health() -> list[dict]:
    return [await get_adapter(c).health() for c in CHANNELS]
