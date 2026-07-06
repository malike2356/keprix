"""Pre-install validation for installer polish."""

from __future__ import annotations

import platform
import shutil
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PreflightCheck:
    name: str
    ok: bool
    message: str
    fix: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ok": self.ok, "message": self.message, "fix": self.fix}


@dataclass
class PreflightReport:
    checks: list[PreflightCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "checks": [check.to_dict() for check in self.checks]}


def _port_available(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) != 0


def run_preflight(*, ports: list[int] | None = None, min_disk_gb: float = 2.0) -> PreflightReport:
    ports = ports or [3000, 3333]
    report = PreflightReport()

    report.checks.append(
        PreflightCheck(
            name="python_version",
            ok=platform.python_version_tuple() >= ("3", "10"),
            message=f"Python {platform.python_version()}",
            fix="Install Python 3.10 or newer",
        )
    )

    for binary in ("docker", "curl"):
        found = shutil.which(binary) is not None
        report.checks.append(
            PreflightCheck(
                name=f"binary_{binary}",
                ok=found,
                message=f"{binary} {'found' if found else 'missing'}",
                fix=None if found else f"Install {binary} and re-run the installer",
            )
        )

    free_gb = shutil.disk_usage(Path.home()).free / (1024**3)
    report.checks.append(
        PreflightCheck(
            name="disk_space",
            ok=free_gb >= min_disk_gb,
            message=f"{free_gb:.1f} GB free",
            fix=f"Free at least {min_disk_gb:.0f} GB before installing",
        )
    )

    for port in ports:
        available = _port_available(port)
        report.checks.append(
            PreflightCheck(
                name=f"port_{port}",
                ok=available,
                message=f"Port {port} {'available' if available else 'in use'}",
                fix=None if available else f"Stop the process on port {port} or run: keprix configure --port {port + 1}",
            )
        )

    return report
