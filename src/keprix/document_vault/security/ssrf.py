"""SSRF defenses for Document Vault URL imports/delivery (Prompt 652)."""

from __future__ import annotations

from urllib.parse import urlparse

from keprix.document_vault.models import VaultError


def assert_safe_fetch_url(url: str) -> str:
    """Reject private/link-local/metadata hosts for vault URL fetch."""
    raw = str(url or "").strip()
    if not raw:
        raise VaultError("invalid_args", "url required")
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise VaultError("ssrf_blocked", "only http/https URLs allowed")
    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise VaultError("ssrf_blocked", "url host required")
    blocked = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "metadata.google.internal",
        "169.254.169.254",
    }
    if host in blocked or host.endswith(".local") or host.endswith(".internal"):
        raise VaultError("ssrf_blocked", f"host {host} is not allowed")
    # Private IPv4 ranges
    if host.startswith("10.") or host.startswith("192.168.") or host.startswith("169.254."):
        raise VaultError("ssrf_blocked", f"host {host} is not allowed")
    if host.startswith("172."):
        try:
            second = int(host.split(".")[1])
            if 16 <= second <= 31:
                raise VaultError("ssrf_blocked", f"host {host} is not allowed")
        except (IndexError, ValueError):
            pass
    try:
        from keprix.security.egress_policy import EgressPolicy

        policy = EgressPolicy()
        if hasattr(policy, "check_url"):
            policy.check_url(raw)
        elif hasattr(policy, "allow_url") and not policy.allow_url(raw):
            raise VaultError("ssrf_blocked", "egress policy denied url")
    except VaultError:
        raise
    except Exception:
        pass
    return raw


__all__ = ["assert_safe_fetch_url"]
