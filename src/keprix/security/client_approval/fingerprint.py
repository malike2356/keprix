"""Privacy-preserving client fingerprints for remote agent approval.

Stores hashes and short summaries only; never raw IP or full request bodies.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from typing import Any


def _salt() -> str:
    return (os.environ.get("KEPRIX_CLIENT_FP_SALT") or "keprix-client-fp-v1").strip()


def hash_ip(ip: str | None) -> str:
    """One-way IP hash (truncated) for network-pattern signals."""
    value = (ip or "").strip() or "unknown"
    digest = hashlib.sha256(f"{_salt()}:ip:{value}".encode("utf-8")).hexdigest()
    return digest[:16]


def summarize_user_agent(user_agent: str | None) -> str:
    ua = (user_agent or "").strip()
    if not ua:
        return "unknown"
    # Keep a short family label only.
    lowered = ua.lower()
    for name in (
        "claude",
        "gpt",
        "openai",
        "cursor",
        "copilot",
        "keprix",
        "python-requests",
        "httpx",
        "curl",
        "axios",
        "node",
        "go-http",
        "okhttp",
        "chrome",
        "firefox",
        "safari",
    ):
        if name in lowered:
            # Include major version digit if present.
            match = re.search(rf"{re.escape(name)}[/\s]?(\d+)", lowered)
            if match:
                return f"{name}/{match.group(1)}"
            return name
    return ua[:48]


@dataclass(frozen=True)
class ClientFingerprint:
    fingerprint: str
    user_agent_summary: str
    ip_hash: str
    agent_label: str
    client_kind: str  # agent | mcp | mobile | desktop | api | unknown

    def to_dict(self) -> dict[str, str]:
        return {
            "fingerprint": self.fingerprint,
            "user_agent_summary": self.user_agent_summary,
            "ip_hash": self.ip_hash,
            "agent_label": self.agent_label,
            "client_kind": self.client_kind,
        }


def detect_client_kind(headers: dict[str, str], user_agent: str | None) -> str:
    lowered = {k.lower(): v for k, v in headers.items()}
    if lowered.get("x-keprix-client") == "mobile" or "keprix-mobile" in (user_agent or "").lower():
        return "mobile"
    if lowered.get("x-keprix-client") == "desktop" or "keprix-desktop" in (user_agent or "").lower():
        return "desktop"
    if lowered.get("x-mcp-client") or "mcp" in (user_agent or "").lower():
        return "mcp"
    if lowered.get("x-agent-id") or lowered.get("x-keprix-agent-id"):
        return "agent"
    ua = (user_agent or "").lower()
    if any(token in ua for token in ("claude", "gpt", "openai", "cursor", "copilot", "agent")):
        return "agent"
    return "api"


def build_client_fingerprint(
    *,
    user_agent: str | None,
    ip: str | None,
    headers: dict[str, str] | None = None,
    token_id: str | None = None,
) -> ClientFingerprint:
    hdrs = {str(k): str(v) for k, v in (headers or {}).items()}
    ua_summary = summarize_user_agent(user_agent)
    ip_digest = hash_ip(ip)
    agent_label = (
        hdrs.get("X-Agent-ID")
        or hdrs.get("x-agent-id")
        or hdrs.get("X-Keprix-Agent-ID")
        or hdrs.get("x-keprix-agent-id")
        or ua_summary
    )
    client_kind = detect_client_kind(hdrs, user_agent)
    material = "|".join(
        [
            _salt(),
            client_kind,
            ua_summary.lower(),
            str(agent_label).lower()[:64],
            ip_digest[:8],  # coarse network bucket, not full IP hash
            (token_id or "")[:36],
        ]
    )
    fingerprint = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return ClientFingerprint(
        fingerprint=fingerprint,
        user_agent_summary=ua_summary,
        ip_hash=ip_digest,
        agent_label=str(agent_label)[:80],
        client_kind=client_kind,
    )


def client_approval_enabled() -> bool:
    raw = (os.environ.get("KEPRIX_CLIENT_APPROVAL_ENABLED") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    try:
        from keprix.billing.wallet.policy import is_hosted_deployment

        return is_hosted_deployment()
    except Exception:
        return False


def token_security_enabled() -> bool:
    raw = (os.environ.get("KEPRIX_TOKEN_SECURITY_ENABLED") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return client_approval_enabled()
