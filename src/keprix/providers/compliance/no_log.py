"""No-log mode: strip or suppress request/response logging for sensitive tenants."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class NoLogConfig:
    enabled: bool = False
    strip_request_body: bool = True
    strip_response_body: bool = True
    audit_meta_only: bool = True    # still log metadata (provider, latency, tokens) but not content


class NoLogPolicy:
    """Enforce no-log behaviour for tenants that require it.

    When enabled:
      - Request message bodies are redacted before any structured logging.
      - Response content is redacted before any structured logging.
      - Only metadata (provider, model, latency, token counts) is written.

    This does NOT control whether the upstream provider logs the request;
    callers should check ``provider_logs`` on the ProviderProfile and route
    to a provider that guarantees no server-side logging.
    """

    def __init__(self, config: NoLogConfig | None = None) -> None:
        self._cfg = config or NoLogConfig()

    @property
    def enabled(self) -> bool:
        return self._cfg.enabled

    def redact_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of the payload safe to pass to the structured logger."""
        if not self._cfg.enabled or not self._cfg.strip_request_body:
            return payload
        safe = dict(payload)
        if "messages" in safe:
            safe["messages"] = [
                {**m, "content": "[REDACTED]"} for m in safe["messages"]
            ]
        for key in ("prompt", "input", "text"):
            if key in safe:
                safe[key] = "[REDACTED]"
        return safe

    def redact_response(self, response: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of the response safe to pass to the structured logger."""
        if not self._cfg.enabled or not self._cfg.strip_response_body:
            return response
        safe = dict(response)
        if "choices" in safe:
            safe["choices"] = [
                {**c, "message": {**c.get("message", {}), "content": "[REDACTED]"}}
                for c in safe["choices"]
            ]
        for key in ("content", "output", "text"):
            if key in safe:
                safe[key] = "[REDACTED]"
        return safe

    def log_request(self, payload: dict[str, Any], level: int = logging.DEBUG) -> None:
        """Log a request, respecting no-log policy."""
        logger.log(level, "Request payload: %r", self.redact_request(payload))

    def log_response(self, response: dict[str, Any], level: int = logging.DEBUG) -> None:
        """Log a response, respecting no-log policy."""
        logger.log(level, "Response payload: %r", self.redact_response(response))
