"""Post-install health checks."""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class HealthCheck:
    name: str
    ok: bool
    detail: str = ""


def _curl_ok(url: str, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        request = Request(url, method="GET")
        with urlopen(request, timeout=timeout) as response:
            return response.status < 500, f"HTTP {response.status}"
    except URLError as exc:
        return False, str(exc.reason)[:120]
    except Exception as exc:
        return False, str(exc)[:120]


def _command_ok(command: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        if result.returncode == 0:
            return True, (result.stdout or "ok").strip()[:80]
        return False, (result.stderr or result.stdout or "failed").strip()[:120]
    except FileNotFoundError:
        return False, "command not found"
    except Exception as exc:
        return False, str(exc)[:120]


def run_health_checks(
    *,
    backend_url: str | None = None,
    frontend_url: str | None = None,
    postgres_host: str = "localhost",
    postgres_port: int = 5432,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_password: str = "",
    searxng_url: str | None = None,
    check_fn: Callable[[str], tuple[bool, str]] | None = None,
) -> list[HealthCheck]:
    probe = check_fn or _curl_ok
    backend = backend_url or os.environ.get("KEPRIX_API_URL", "http://127.0.0.1:3333/api/health")
    frontend = frontend_url or os.environ.get("KEPRIX_FRONTEND_URL", "http://127.0.0.1:3000")
    searxng = searxng_url or os.environ.get("KEPRIX_SEARXNG_URL", "http://127.0.0.1:8080")

    checks: list[HealthCheck] = []

    ok, detail = probe(backend)
    checks.append(HealthCheck("backend", ok, detail))

    ok, detail = probe(frontend)
    checks.append(HealthCheck("frontend", ok, detail))

    pg_cmd = ["pg_isready", "-h", postgres_host, "-p", str(postgres_port)]
    ok, detail = _command_ok(pg_cmd)
    checks.append(HealthCheck("postgres", ok, detail))

    redis_cmd = ["redis-cli", "-h", redis_host, "-p", str(redis_port)]
    if redis_password:
        redis_cmd.extend(["-a", redis_password, "ping"])
    else:
        redis_cmd.append("ping")
    ok, detail = _command_ok(redis_cmd)
    checks.append(HealthCheck("redis", ok, detail))

    ok, detail = probe(f"{searxng.rstrip('/')}/healthz")
    checks.append(HealthCheck("searxng", ok, detail))
    return checks


def format_health_table(checks: list[HealthCheck]) -> str:
    lines = [f"{'Service':<12} {'Status':<8} Detail", "-" * 60]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        lines.append(f"{check.name:<12} {status:<8} {check.detail}")
    return "\n".join(lines)


def all_passed(checks: list[HealthCheck]) -> bool:
    return all(check.ok for check in checks)


def wait_for_healthy(
    *,
    timeout_seconds: int = 120,
    interval_seconds: float = 3.0,
    runner: Callable[[], list[HealthCheck]] | None = None,
) -> bool:
    runner = runner or (lambda: run_health_checks())
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        checks = runner()
        if all_passed(checks):
            return True
        time.sleep(interval_seconds)
    return False


def main() -> int:
    checks = run_health_checks()
    print(format_health_table(checks))
    return 0 if all_passed(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
