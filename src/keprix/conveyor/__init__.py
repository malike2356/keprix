"""Prototype-to-production conveyor (parity with shared/conveyor)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

Severity = Literal["critical", "warning", "info"]
LayerId = str

SKIP_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
    "vendor",
}

CRITICAL_LAYERS = {
    "security",
    "error-handling",
    "environment",
    "secrets",
    "sessions",
    "deployment",
}
DEFAULT_THRESHOLD = 80

KEEP_DOT = {".env", ".gitignore", ".env.example", ".pre-commit-config.yaml", ".github"}


@dataclass
class Finding:
    severity: Severity
    message: str
    suggested_fix: str
    file: str | None = None


@dataclass
class LayerResult:
    id: str
    name: str
    score: int
    critical: bool
    findings: list[Finding] = field(default_factory=list)
    passed: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "score": self.score,
            "critical": self.critical,
            "passed": self.passed,
            "findings": [
                {
                    "severity": f.severity,
                    "message": f.message,
                    "file": f.file,
                    "suggestedFix": f.suggested_fix,
                }
                for f in self.findings
            ],
        }


def _walk(root: Path, max_files: int = 4000) -> list[Path]:
    out: list[Path] = []
    stack = [root]
    while stack and len(out) < max_files:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for ent in entries:
            name = ent.name
            if name in SKIP_DIRS:
                continue
            if name.startswith(".") and name not in KEEP_DOT:
                continue
            if ent.is_dir():
                stack.append(ent)
            else:
                out.append(ent)
    return out


def _score(findings: list[Finding], critical: bool) -> int:
    score = 100
    for f in findings:
        if f.severity == "critical":
            score -= 35 if critical else 25
        elif f.severity == "warning":
            score -= 12
        else:
            score -= 4
    return max(0, min(100, score))


def _layer(id_: str, name: str, findings: list[Finding], threshold: int = DEFAULT_THRESHOLD) -> LayerResult:
    critical = id_ in CRITICAL_LAYERS
    score = _score(findings, critical)
    return LayerResult(
        id=id_,
        name=name,
        score=score,
        critical=critical,
        findings=findings,
        passed=score >= threshold,
    )


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def run_full_audit(project_path: str | Path, threshold: int = DEFAULT_THRESHOLD) -> dict[str, Any]:
    root = Path(project_path).resolve()
    files = _walk(root)
    rel = lambda p: str(p.relative_to(root))

    def texts() -> list[tuple[Path, str]]:
        return [(f, _read(f)) for f in files]

    # security
    findings: list[Finding] = []
    blob = "\n".join(t for _, t in texts())
    if not re.search(r"cors|Access-Control-Allow|helmet\(", blob, re.I):
        findings.append(Finding("critical", "No CORS / helmet / security middleware patterns found", "Add helmet() or CORS allowlist."))
    if not re.search(r"get_current_user|requireAuth|authorizeOps|jwt\.verify", blob, re.I):
        findings.append(Finding("warning", "No obvious auth gate helpers found", "Protect mutating routes with auth middleware."))
    layers = [_layer("security", "Security", findings, threshold)]

    # error-handling
    findings = []
    for f, t in texts():
        if re.search(r"res\.(json|send)\([^)]*err\.stack|stack:\s*err", t, re.I):
            findings.append(Finding("critical", "Stack traces may be returned to clients", "Return generic public errors.", rel(f)))
    if not re.search(r"publicError|toPublicError|safeError|INTERNAL_ERROR", blob, re.I):
        findings.append(Finding("warning", "No public/private error separation helper detected", "Introduce publicError helper."))
    layers.append(_layer("error-handling", "Error handling", findings, threshold))

    # environment
    findings = []
    gi = next(( _read(f) for f in files if f.name == ".gitignore"), "")
    env_file = next((f for f in files if f.name == ".env"), None)
    if env_file and ".env" not in gi:
        findings.append(Finding("critical", ".env present but not ignored by .gitignore", "Add .env to .gitignore.", rel(env_file)))
    if not any(f.name == ".env.example" for f in files):
        findings.append(Finding("warning", "No .env.example documenting required variables", "Add .env.example placeholders."))
    for f, t in texts():
        if re.search(r"DATABASE_URL=.*localhost|shared.?db", t, re.I):
            findings.append(Finding("critical", "Possible shared/dev database URL baked into tree", "Use distinct DATABASE_URL per env.", rel(f)))
            break
    layers.append(_layer("environment", "Environment separation", findings, threshold))

    # logging
    findings = []
    if not re.search(r"pino\(|winston\.|logger\.(info|error)", blob, re.I):
        findings.append(Finding("warning", "No structured logger usage detected", "Adopt structured JSON logging."))
    layers.append(_layer("logging", "Logging", findings, threshold))

    # monitoring
    findings = []
    if not re.search(r"/health|healthcheck|readiness|liveness", blob, re.I):
        findings.append(Finding("critical", "No health/readiness endpoint patterns found", "Expose GET /health."))
    layers.append(_layer("monitoring", "Monitoring", findings, threshold))

    # rate-limiting
    findings = []
    if not re.search(r"rateLimit|rate-limit|slowapi|throttle", blob, re.I):
        findings.append(Finding("critical", "No API rate limiting middleware detected", "Add per-IP rate limits."))
    layers.append(_layer("rate-limiting", "Rate limiting", findings, threshold))

    # secrets
    findings = []
    secret_re = re.compile(
        r"(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{12,}['\"]|sk-[A-Za-z0-9]{10,}",
        re.I,
    )
    for f, t in texts():
        if f.name.endswith(".env.example"):
            continue
        if secret_re.search(t) and f.name != ".env":
            findings.append(Finding("critical", "Possible hardcoded secret in source", "Move secrets to env/vault.", rel(f)))
    if ".env" not in gi:
        findings.append(Finding("critical", ".env not listed in .gitignore", "Ignore .env files."))
    layers.append(_layer("secrets", "Secret management", findings, threshold))

    # sessions
    findings = []
    if not re.search(r"session|maxAge|cookie\.|revokeSession", blob, re.I):
        findings.append(Finding("critical", "No session/cookie expiration patterns found", "Set session maxAge and revocation."))
    layers.append(_layer("sessions", "Session management", findings, threshold))

    # accessibility
    ui = [f for f in files if f.suffix.lower() in {".tsx", ".jsx", ".vue", ".html"}]
    findings = []
    if ui and not any(re.search(r"aria-|alt=|role=", _read(f), re.I) for f in ui):
        findings.append(Finding("warning", "UI files lack obvious aria/alt/role attributes", "Add WCAG AA labels."))
    layers.append(_layer("accessibility", "Accessibility", findings, threshold))

    # compliance
    findings = []
    if not re.search(r"gdpr|privacy.?policy|consent", blob, re.I):
        findings.append(Finding("warning", "No GDPR/privacy consent patterns found", "Add consent gates."))
    layers.append(_layer("compliance", "Compliance", findings, threshold))

    # performance
    findings = []
    if not re.search(r"cache|redis|CDN|etag", blob, re.I):
        findings.append(Finding("warning", "No caching strategy signals found", "Add caching for hot reads."))
    layers.append(_layer("performance", "Performance", findings, threshold))

    # backup
    findings = []
    if not re.search(r"backup|disaster.?recovery|pg_dump|restore", blob, re.I) and not any(
        "backup" in f.name.lower() for f in files
    ):
        findings.append(Finding("critical", "No backup/DR documentation or scripts found", "Document backup/restore drills."))
    layers.append(_layer("backup", "Backup and recovery", findings, threshold))

    # deployment
    findings = []
    if not any(".github/workflows" in str(f) for f in files):
        findings.append(Finding("critical", "No CI workflow files found", "Add GitHub Actions CI."))
    if not re.search(r"rollback|blue.?green|deploy-atomic", blob, re.I):
        findings.append(Finding("warning", "No rollback / blue-green deploy references found", "Automate rollback."))
    layers.append(_layer("deployment", "Deployment", findings, threshold))

    overall = round(sum(l.score for l in layers) / max(len(layers), 1))
    critical_failures = [l for l in layers if l.critical and l.score < threshold]
    passed = len(critical_failures) == 0
    return {
        "projectPath": str(root),
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "layers": [l.as_dict() for l in layers],
        "overallScore": overall,
        "passed": passed,
        "threshold": threshold,
        "criticalFailures": [l.as_dict() for l in critical_failures],
        "summary": (
            f"Passed: all critical layers score >= {threshold} (overall {overall})."
            if passed
            else f"Failed: {len(critical_failures)} critical layer(s) below {threshold} (overall {overall})."
        ),
    }


def generate_fix(layer_id: str, message: str, file: str | None = None, suggested_fix: str | None = None) -> dict[str, Any]:
    body = suggested_fix or "Follow the audit suggestedFix."
    return {
        "layerId": layer_id,
        "findingMessage": message,
        "title": f"Address: {message[:72]}",
        "patchOrConfig": body + "\n",
        "requiresHumanApproval": True,
        "confidence": 0.8,
        "file": file,
    }


def generate_fixes_for_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    fixes: list[dict[str, Any]] = []
    for layer in report.get("layers") or []:
        for finding in layer.get("findings") or []:
            if finding.get("severity") == "info":
                continue
            fixes.append(
                generate_fix(
                    layer["id"],
                    finding["message"],
                    finding.get("file"),
                    finding.get("suggestedFix"),
                )
            )
    return fixes


_STATUS: dict[str, Any] = {
    "state": "idle",
    "targetEnv": "none",
    "message": "Conveyor idle",
    "updatedAt": datetime.now(timezone.utc).isoformat(),
}


def pipeline_status() -> dict[str, Any]:
    return dict(_STATUS)


def run_pipeline(
    project_path: str | Path,
    target_env: str,
    *,
    human_approval: bool = False,
) -> dict[str, Any]:
    global _STATUS
    _STATUS = {
        "state": "auditing",
        "targetEnv": target_env,
        "message": "Running 13-layer audit",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    report = run_full_audit(project_path)
    fixes = generate_fixes_for_report(report)
    if not report["passed"]:
        _STATUS = {
            "state": "failed",
            "targetEnv": target_env,
            "message": report["summary"],
            "report": report,
            "fixes": fixes,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        return {"status": dict(_STATUS), "report": report, "fixes": fixes, "deployed": False}
    if not human_approval:
        _STATUS = {
            "state": "awaiting_approval",
            "targetEnv": target_env,
            "message": "Audit passed; set human_approval=true to deploy.",
            "report": report,
            "fixes": fixes,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        return {"status": dict(_STATUS), "report": report, "fixes": fixes, "deployed": False}
    _STATUS = {
        "state": "passed",
        "targetEnv": target_env,
        "message": f"Pipeline passed for {target_env}",
        "report": report,
        "fixes": fixes,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    return {"status": dict(_STATUS), "report": report, "fixes": fixes, "deployed": False}


def default_keprix_root() -> Path:
    return Path(__file__).resolve().parents[3]
