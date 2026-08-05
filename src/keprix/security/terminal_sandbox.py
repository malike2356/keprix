"""Policy-based terminal command sandbox."""

from __future__ import annotations

import os
import shutil
import shlex
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SandboxPolicy:
    allowed_paths: set[str] = field(default_factory=set)
    read_only_paths: set[str] = field(default_factory=set)
    denied_paths: set[str] = field(default_factory=set)
    deny_paths_outside_allowed: bool = True
    allow_egress: bool = False
    allowed_hosts: set[str] = field(default_factory=set)
    allowed_ports: set[int] = field(default_factory=lambda: {80, 443})
    deny_egress_by_default: bool = True
    allowed_commands: set[str] = field(default_factory=set)
    denied_commands: set[str] = field(default_factory=set)
    allow_pipes: bool = True
    allow_redirects: bool = False
    allow_subshells: bool = False
    allow_background: bool = False
    max_runtime_seconds: int = 30
    max_output_bytes: int = 100_000
    max_memory_mb: int = 256


POLICY_RESTRICTED = SandboxPolicy(
    allowed_paths={"/tmp"},
    denied_paths={"/", "/etc", "/home", "/root", "/var", "/opt", "/usr", "/boot", "/sys", "/proc", "/dev"},
    allowed_commands={"echo", "cat", "ls", "pwd", "wc", "head", "tail", "grep", "find", "sort", "uniq"},
    denied_commands={"rm", "mv", "cp", "dd", "shred", "mkfs", "mount", "umount", "chmod", "chown", "sudo", "su"},
)

POLICY_STANDARD = SandboxPolicy(
    allowed_paths={str(Path.home()), "/tmp", "/opt/lampp/htdocs/verlox"},
    read_only_paths={"/etc", "/usr", "/opt"},
    denied_paths={"/root", "/boot", "/sys", "/proc", "/dev", "/var/log"},
    allow_egress=True,
    allowed_hosts={"api.openai.com", "api.anthropic.com", "github.com", "pypi.org"},
    allowed_commands=set(),
    denied_commands={"sudo", "su", "passwd", "mkfs", "mount", "umount", "iptables", "ufw", "systemctl", "docker", "podman", "kubectl"},
    allow_redirects=True,
)


class SandboxViolation(RuntimeError):
    pass


class TerminalSandbox:
    def __init__(self, policy: SandboxPolicy = POLICY_RESTRICTED) -> None:
        self.policy = policy

    def validate(self, command: str, workdir: str | None = None) -> None:
        if not self.policy.allow_subshells and ("$(" in command or "`" in command):
            raise SandboxViolation("Subshells are not allowed")
        if not self.policy.allow_background and "&" in command:
            raise SandboxViolation("Background execution is not allowed")
        if not self.policy.allow_redirects and any(token in command for token in [">", "<"]):
            raise SandboxViolation("Shell redirects are not allowed")
        if not self.policy.allow_pipes and "|" in command:
            raise SandboxViolation("Pipes are not allowed")
        parts = shlex.split(command)
        if not parts:
            raise SandboxViolation("Empty command")
        binary = Path(parts[0]).name
        if binary in self.policy.denied_commands:
            raise SandboxViolation(f"Command denied: {binary}")
        if self.policy.allowed_commands and binary not in self.policy.allowed_commands:
            raise SandboxViolation(f"Command not allowed: {binary}")
        if workdir:
            self._validate_path(workdir)

    def _validate_path(self, path: str) -> None:
        resolved = str(Path(path).expanduser().resolve())
        if any(resolved == denied or resolved.startswith(denied.rstrip("/") + "/") for denied in self.policy.denied_paths):
            raise SandboxViolation(f"Path denied: {path}")
        if self.policy.deny_paths_outside_allowed and self.policy.allowed_paths:
            if not any(resolved == allowed.rstrip("/") or resolved.startswith(allowed.rstrip("/") + "/") for allowed in self.policy.allowed_paths):
                raise SandboxViolation(f"Path outside allowed roots: {path}")

    def execute(self, command: str, workdir: str | None = None) -> str:
        self.validate(command, workdir)
        sandbox_dir = tempfile.mkdtemp(prefix="keprix_sandbox_")
        env = {"PATH": os.environ.get("PATH", ""), "HOME": sandbox_dir, "TMPDIR": sandbox_dir}
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=workdir or sandbox_dir,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=self.policy.max_runtime_seconds,
                check=False,
            )
            return result.stdout[: self.policy.max_output_bytes]
        finally:
            shutil.rmtree(sandbox_dir, ignore_errors=True)
