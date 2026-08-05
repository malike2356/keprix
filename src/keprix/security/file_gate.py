"""Filesystem access gate for agent tools."""

from __future__ import annotations

from pathlib import Path

from keprix.security.terminal_sandbox import SandboxPolicy, SandboxViolation


class FileAccessGate:
    def __init__(self, policy: SandboxPolicy) -> None:
        self.policy = policy

    def check(self, path: str, *, write: bool = False) -> Path:
        resolved = Path(path).expanduser().resolve()
        text = str(resolved)
        if any(text == denied.rstrip("/") or text.startswith(denied.rstrip("/") + "/") for denied in self.policy.denied_paths):
            raise SandboxViolation(f"Path denied: {path}")
        if write and any(text == root.rstrip("/") or text.startswith(root.rstrip("/") + "/") for root in self.policy.read_only_paths):
            raise SandboxViolation(f"Path is read-only: {path}")
        if self.policy.deny_paths_outside_allowed and self.policy.allowed_paths:
            if not any(text == root.rstrip("/") or text.startswith(root.rstrip("/") + "/") for root in self.policy.allowed_paths):
                raise SandboxViolation(f"Path outside allowed roots: {path}")
        return resolved
