"""HTTP client factory for Keprix tools.

All tools that need to make HTTP requests MUST use get_http_client() instead
of creating httpx.AsyncClient directly. This returns a gate-enforced client
that validates outbound requests against the product's egress policy.

Migration guide (for existing tool code):
  Before: client = httpx.AsyncClient()
  After:  client = get_http_client()

  Before: async with httpx.AsyncClient() as client:
  After:  async with get_http_client() as client:
"""

from __future__ import annotations

from typing import Any

import httpx

from keprix.security.egress_gate import get_egress_gate


def get_http_client(
    product_id: str | None = None,
    **kwargs: Any,
) -> httpx.AsyncClient:
    """Return an egress-gate-enforced httpx.AsyncClient.

    The client validates all outbound requests against the current product's
    egress allowlist. Requests to private/loopback IPs or undeclared hosts
    raise EgressBlocked before the TCP connection is established.

    Args:
        product_id: Override the product_id for this client. If None,
                    reads from the current ProductContext (set by middleware).
        **kwargs: Forwarded to httpx.AsyncClient (timeout, headers, etc.)

    Raises:
        RuntimeError: If neither product_id nor a ProductContext is available.

    Usage::

        async with get_http_client() as client:
            response = await client.get("https://api.sendgrid.com/v3/stats")
    """
    gate = get_egress_gate()
    return gate.get_client(product_id=product_id, **kwargs)
