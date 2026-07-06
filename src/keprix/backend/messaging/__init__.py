"""Ambient room messaging (Prompt 45)."""

from keprix.backend.messaging.gateway import MessageGateway, get_message_gateway
from keprix.backend.messaging.schemas import RoomConfig

__all__ = ["MessageGateway", "RoomConfig", "get_message_gateway"]
