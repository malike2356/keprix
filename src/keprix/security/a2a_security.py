"""A2A message signing and replay protection."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class A2AMessage:
    sender_id: str
    recipient_id: str
    action: str
    payload: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    nonce: str = field(default_factory=lambda: uuid.uuid4().hex)
    signature: str = ""


class A2ASecurityManager:
    def __init__(self, agent_id: str, secret: str, *, max_age_seconds: int = 300) -> None:
        self.agent_id = agent_id
        self.secret = secret.encode("utf-8")
        self.max_age_seconds = max_age_seconds
        self._seen_nonces: set[str] = set()

    def sign_message(self, recipient_id: str, action: str, payload: dict[str, Any]) -> A2AMessage:
        message = A2AMessage(sender_id=self.agent_id, recipient_id=recipient_id, action=action, payload=payload)
        message.signature = self._signature(message)
        return message

    def verify_message(self, message: A2AMessage) -> tuple[bool, str]:
        if message.recipient_id != self.agent_id:
            return False, "wrong_recipient"
        if abs(time.time() - message.timestamp) > self.max_age_seconds:
            return False, "expired"
        if message.nonce in self._seen_nonces:
            return False, "replay"
        expected = self._signature(message)
        if not hmac.compare_digest(expected, message.signature):
            return False, "bad_signature"
        self._seen_nonces.add(message.nonce)
        return True, "ok"

    def _signature(self, message: A2AMessage) -> str:
        body = json.dumps(
            {
                "sender_id": message.sender_id,
                "recipient_id": message.recipient_id,
                "action": message.action,
                "payload": message.payload,
                "timestamp": message.timestamp,
                "nonce": message.nonce,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hmac.new(self.secret, body, hashlib.sha256).hexdigest()
