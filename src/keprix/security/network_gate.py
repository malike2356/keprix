"""Network egress gate for tools and agent requests."""

from __future__ import annotations

from urllib.parse import urlparse

from keprix.security.terminal_sandbox import SandboxPolicy, SandboxViolation


class NetworkGate:
    def __init__(self, policy: SandboxPolicy) -> None:
        self.policy = policy

    def check_url(self, url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not self.policy.allow_egress:
            raise SandboxViolation("Network egress is disabled")
        if self.policy.deny_egress_by_default and host not in self.policy.allowed_hosts:
            raise SandboxViolation(f"Host denied: {host}")
        if port not in self.policy.allowed_ports:
            raise SandboxViolation(f"Port denied: {port}")
        return True
