"""Security audit runner for WARDEN."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from keprix.compat import UTC, StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix.playbook.runtime.graph import END, PlaybookGraph
from keprix.playbook.runtime.runner import PlaybookRunner
from keprix.personas.warden.persona import WARDEN_PERSONA
from keprix.security.crypto import derive_key, encrypt_text
from keprix.security.headers import build_security_headers
from keprix.security.patterns import SECRET_PATTERNS
from keprix.security.prompt_guard import analyze_prompt
from keprix.security.secret_scan import get_secret_scanner


class Severity(StrEnum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


OUT_OF_SCOPE_KEYWORDS = [
    "penetration test",
    "pentest",
    "exploit",
    "osint",
    "reconnaissance",
    "packet capture",
    "wireshark",
    "forensics",
    "reverse engineer",
    "siem",
    "threat intelligence",
    "vulnerability exploitation",
    "network interception",
]


KNOWN_VULNERABLE_PACKAGES: dict[str, dict[str, str]] = {
    "pillow": {"below": "10.0.1", "cve": "CVE-2023-44271", "severity": Severity.HIGH},
    "requests": {"below": "2.31.0", "cve": "CVE-2023-32681", "severity": Severity.MEDIUM},
    "urllib3": {"below": "2.0.7", "cve": "CVE-2023-45803", "severity": Severity.MEDIUM},
}


@dataclass(slots=True)
class AuditFinding:
    rule: str
    severity: str
    message: str
    remediation: str
    category: str = "general"

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
            "remediation": self.remediation,
            "category": self.category,
        }


@dataclass
class AuditReport:
    audit_id: str
    workspace_id: str
    findings: list[AuditFinding] = field(default_factory=list)
    out_of_scope: bool = False
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    encrypted_storage: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "audit_id": self.audit_id,
            "workspace_id": self.workspace_id,
            "findings": [finding.to_dict() for finding in self.findings],
            "out_of_scope": self.out_of_scope,
            "generated_at": self.generated_at,
            "summary": self.summary(),
        }
        if self.encrypted_storage:
            payload["encrypted_storage"] = self.encrypted_storage
        return payload

    def summary(self) -> dict[str, int]:
        counts = {level.value: 0 for level in Severity}
        for finding in self.findings:
            if finding.severity in counts:
                counts[finding.severity] += 1
        return counts


class WardenAuditor:
    def __init__(self, *, workspace_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.persona = WARDEN_PERSONA
        self._checklist_path = Path(__file__).resolve().parent / "prompts" / "audit_checklist.md"
        self._incident_path = Path(__file__).resolve().parent / "prompts" / "incident.md"
        self._reports_dir = Path.home() / ".keprix" / "warden" / "audits" / workspace_id
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def audit_encryption_key(self) -> str:
        return os.environ.get("KEPRIX_AUDIT_ENCRYPTION_KEY") or f"warden-audit-{self.workspace_id}"

    def persist_encrypted_report(self, report: AuditReport) -> dict[str, str]:
        stored = self.encrypt_report(report, encryption_key=self.audit_encryption_key())
        path = self._reports_dir / f"{report.audit_id}.enc.json"
        path.write_text(json.dumps(stored), encoding="utf-8")
        return stored

    def is_out_of_scope(self, request: str) -> bool:
        text = request.lower()
        return any(keyword in text for keyword in OUT_OF_SCOPE_KEYWORDS)

    def audit_configuration(self, config: dict[str, Any]) -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        if config.get("debug", False):
            findings.append(
                AuditFinding(
                    rule="debug_disabled",
                    severity=Severity.HIGH,
                    message="Debug mode is enabled",
                    remediation="Set debug=false in production configuration",
                    category="configuration",
                )
            )

        if not config.get("rate_limit_enabled", True):
            findings.append(
                AuditFinding(
                    rule="rate_limiting",
                    severity=Severity.MEDIUM,
                    message="Rate limiting is disabled",
                    remediation="Enable rate limiting on public API endpoints",
                    category="configuration",
                )
            )

        headers = build_security_headers(https_enabled=bool(config.get("https_enabled")))
        if "Content-Security-Policy" not in headers:
            findings.append(
                AuditFinding(
                    rule="security_headers",
                    severity=Severity.MEDIUM,
                    message="Content-Security-Policy header missing",
                    remediation="Enable security headers middleware",
                    category="configuration",
                )
            )

        return findings

    def audit_content(self, text: str, *, source: str = "content") -> list[AuditFinding]:
        findings: list[AuditFinding] = []

        for pattern in SECRET_PATTERNS:
            if pattern.pattern.search(text):
                findings.append(
                    AuditFinding(
                        rule=f"secret_{pattern.name}",
                        severity=Severity.CRITICAL,
                        message=f"Secret pattern detected in {source}: {pattern.name}",
                        remediation="Rotate the exposed credential and move it to the vault",
                        category="secrets",
                    )
                )

        guard = analyze_prompt(text)
        if guard.suspicious:
            findings.append(
                AuditFinding(
                    rule="prompt_injection",
                    severity=Severity.HIGH,
                    message=f"Suspicious prompt patterns in {source}: {', '.join(guard.patterns)}",
                    remediation="Review input source and enable prompt guard logging",
                    category="application",
                )
            )

        scanner = get_secret_scanner()
        sanitized = scanner.scan_and_sanitize(text)
        if sanitized != text:
            findings.append(
                AuditFinding(
                    rule="secret_scan",
                    severity=Severity.CRITICAL,
                    message=f"Secret scanner flagged content in {source}",
                    remediation="Redact secrets before storage or transmission",
                    category="secrets",
                )
            )

        return findings

    def audit_dependencies(self, requirements: list[str]) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        version_re = re.compile(r"^([a-zA-Z0-9_-]+)(?:[=<>!~]+(.+))?$")

        for line in requirements:
            cleaned = line.strip()
            if not cleaned or cleaned.startswith("#"):
                continue
            match = version_re.match(cleaned.split("[", 1)[0])
            if not match:
                continue
            package = match.group(1).lower()
            version = (match.group(2) or "").strip()

            if package in KNOWN_VULNERABLE_PACKAGES:
                advisory = KNOWN_VULNERABLE_PACKAGES[package]
                if not version or version.startswith("<"):
                    findings.append(
                        AuditFinding(
                            rule="cve_advisory",
                            severity=advisory["severity"],
                            message=f"{package} may be affected by {advisory['cve']}",
                            remediation=f"Upgrade {package} to >= {advisory['below']}",
                            category="dependencies",
                        )
                    )

            if not version and package not in {"keprix"}:
                findings.append(
                    AuditFinding(
                        rule="unpinned_dependency",
                        severity=Severity.MEDIUM,
                        message=f"Dependency {package} is not pinned to a version",
                        remediation=f"Pin {package} to a specific version in lockfile or requirements",
                        category="dependencies",
                    )
                )

        return findings

    def run_audit(
        self,
        *,
        request: str = "",
        config: dict[str, Any] | None = None,
        content_samples: list[str] | None = None,
        requirements: list[str] | None = None,
        store_encrypted: bool = True,
    ) -> AuditReport:
        report = AuditReport(audit_id=str(uuid4()), workspace_id=self.workspace_id)

        if request and self.is_out_of_scope(request):
            report.out_of_scope = True
            report.findings.append(
                AuditFinding(
                    rule="out_of_scope",
                    severity=Severity.LOW,
                    message="Request is out of scope for WARDEN (belongs to a security extension)",
                    remediation="Use a security-focused extension for offensive security, forensics, and OSINT",
                    category="policy",
                )
            )
            return report

        if config:
            report.findings.extend(self.audit_configuration(config))
        for index, sample in enumerate(content_samples or []):
            report.findings.extend(self.audit_content(sample, source=f"sample_{index}"))
        if requirements:
            report.findings.extend(self.audit_dependencies(requirements))

        if store_encrypted and report.findings and not report.out_of_scope:
            report.encrypted_storage = self.persist_encrypted_report(report)

        return report

    def encrypt_report(self, report: AuditReport, *, encryption_key: str) -> dict[str, str]:
        key = derive_key(encryption_key, salt=b"warden-audit-v1")
        payload = json.dumps(report.to_dict())
        encrypted = encrypt_text(payload, key)
        return {
            "audit_id": report.audit_id,
            "encrypted": encrypted,
            "algorithm": "AES-256-GCM",
            "stored_at": datetime.now(UTC).isoformat(),
        }

    def render_incident_report(
        self,
        *,
        incident_id: str,
        severity: str,
        summary: str,
        findings: list[AuditFinding],
        immediate_actions: list[str] | None = None,
    ) -> str:
        template = self._incident_path.read_text(encoding="utf-8")
        finding_rows = "\n".join(
            f"| {f.severity} | {f.message} | {f.remediation} |" for f in findings
        ) or "| - | No findings | - |"
        replacements = {
            "{{incident_id}}": incident_id,
            "{{severity}}": severity,
            "{{detected_at}}": datetime.now(UTC).isoformat(),
            "{{status}}": "open",
            "{{summary}}": summary,
            "{{timeline}}": "- Detection logged by WARDEN audit",
            "{{finding_rows}}": finding_rows,
            "{{immediate_actions}}": "\n".join(f"- {action}" for action in (immediate_actions or ["Review findings", "Rotate exposed credentials"])),
            "{{containment_steps}}": "- Isolate affected workspace\n- Disable compromised API keys",
            "{{recovery_steps}}": "- Apply hardening recommendations\n- Re-run audit to verify",
            "{{rca_required}}": "yes" if any(f.severity in {Severity.CRITICAL, Severity.HIGH} for f in findings) else "no",
            "{{lessons_learned}}": "Pending post-incident review",
        }
        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)
        return rendered

    def build_audit_playbook(self) -> PlaybookGraph:
        graph = PlaybookGraph("warden-audit")

        async def scan_node(state: dict[str, Any]) -> dict[str, Any]:
            auditor = WardenAuditor(workspace_id=state.get("workspace_id", "default"))
            report = auditor.run_audit(
                config=state.get("config"),
                content_samples=state.get("content_samples"),
                requirements=state.get("requirements"),
            )
            state["audit_report"] = report.to_dict()
            state["findings"] = [f.to_dict() for f in report.findings]
            return state

        async def summarize_node(state: dict[str, Any]) -> dict[str, Any]:
            findings = state.get("findings", [])
            state["audit_summary"] = {
                "total": len(findings),
                "critical": sum(1 for f in findings if f.get("severity") == Severity.CRITICAL),
                "high": sum(1 for f in findings if f.get("severity") == Severity.HIGH),
            }
            return state

        graph.add_node("scan", scan_node)
        graph.add_node("summarize", summarize_node)
        graph.add_edge("scan", "summarize")
        graph.add_edge("summarize", END)
        return graph

    async def run_audit_playbook(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        graph = self.build_audit_playbook()
        runner = PlaybookRunner(graph.compile())
        run = await runner.execute_inline({**initial_state, "workspace_id": self.workspace_id})
        return {
            "status": run.status.value,
            "audit_report": run.state.get("audit_report"),
            "audit_summary": run.state.get("audit_summary"),
            "playbook_state": run.state,
        }
