"""Safety scan for pack contents."""

from __future__ import annotations

import re
from pathlib import Path

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
]

RISKY_PERMISSIONS = {"network:egress", "shell:execute", "filesystem:write", "credentials:read"}


def scan_pack_dir(pack_dir: Path, manifest_permissions: list[str]) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {"secrets": [], "permissions": []}
    for path in pack_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "manifest.json":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = str(path.relative_to(pack_dir))
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings["secrets"].append(rel)
                break
    undeclared = sorted(set(manifest_permissions) & RISKY_PERMISSIONS)
    if undeclared:
        findings["permissions"] = undeclared
    return findings


def requires_approval(risk_level: str, findings: dict[str, list[str]]) -> bool:
    if risk_level == "high":
        return True
    if findings.get("secrets"):
        return True
    if findings.get("permissions") and risk_level != "low":
        return True
    return False
