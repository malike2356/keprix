"""Enroll this Keprix instance with a governance provider."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from keprix.config.constants import PRODUCT_VERSION
from keprix.governance.signing import sign_payload


class GovernanceEnrollmentError(RuntimeError):
    pass


async def enroll_instance(
    *,
    provider_endpoint: str,
    api_key: str,
    instance_id: str | None = None,
) -> str:
    instance_id = instance_id or str(uuid.uuid4())
    payload = {
        "instance_id": instance_id,
        "product": "keprix",
        "version": PRODUCT_VERSION,
        "enrolled_at": datetime.now(timezone.utc).isoformat(),
    }
    import json

    body = json.dumps(payload).encode("utf-8")
    signature = sign_payload(api_key, body)
    url = f"{provider_endpoint.rstrip('/')}/api/v1/enroll"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Governance-Signature": f"sha256={signature}",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, content=body, headers=headers)
    except httpx.HTTPError as exc:
        raise GovernanceEnrollmentError(f"Could not reach governance provider: {exc}") from exc

    if response.status_code >= 400:
        raise GovernanceEnrollmentError(f"Governance enrollment failed ({response.status_code}): {response.text[:300]}")

    data: dict[str, Any] = {}
    try:
        data = response.json()
    except Exception:
        pass
    return str(data.get("instance_id") or instance_id)
