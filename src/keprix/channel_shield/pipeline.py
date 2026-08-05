"""Shared Channel Shield analysis pipeline (stages A-G)."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from keprix.channel_shield.config import ChannelShieldConfig, load_channel_shield_config
from keprix.channel_shield.crypto_store import read_raw_blob
from keprix.channel_shield.types import (
    PipelineReport,
    ShieldAttachment,
    ShieldEnvelope,
    StageResult,
    Verdict,
)

# Standard EICAR test string (harmless antivirus test file)
EICAR = (
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
)

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

SUSPICIOUS_TLDS = {".zip", ".mov", ".top", ".xyz", ".ru", ".cn"}
PHISH_KEYWORDS = (
    "verify your account",
    "urgent action required",
    "password expires",
    "click here immediately",
    "wire transfer",
    "gift card",
    "crypto wallet",
)


def extract_links(text: str) -> list[str]:
    return list(dict.fromkeys(URL_RE.findall(text or "")))


def _stage_parse(envelope: ShieldEnvelope) -> StageResult:
    findings: list[str] = []
    if not envelope.channel:
        findings.append("missing channel")
    if not envelope.external_message_id:
        findings.append("missing external_message_id")
    if not envelope.from_addr and not envelope.text and not envelope.attachments:
        findings.append("empty envelope")
    if not envelope.links and envelope.text:
        envelope.links = extract_links(envelope.text)
    return StageResult(
        stage="A_parse",
        ok=not findings,
        findings=findings,
        details={"link_count": len(envelope.links), "attachment_count": len(envelope.attachments)},
    )


def _stage_identity(envelope: ShieldEnvelope) -> StageResult:
    findings: list[str] = []
    auth = envelope.auth_signals or {}
    spf = str(auth.get("spf") or "").lower()
    dkim = str(auth.get("dkim") or "").lower()
    dmarc = str(auth.get("dmarc") or "").lower()
    if envelope.channel == "email":
        if spf in {"fail", "softfail"}:
            findings.append(f"spf={spf}")
        if dkim == "fail":
            findings.append("dkim=fail")
        if dmarc == "fail":
            findings.append("dmarc=fail")
    signed = auth.get("signed")
    if signed is False:
        findings.append("ingress signature missing or invalid")
    return StageResult(
        stage="B_identity",
        ok=True,
        findings=findings,
        details={"auth": dict(auth)},
    )


def _stage_url_intel(envelope: ShieldEnvelope) -> StageResult:
    findings: list[str] = []
    details: dict[str, Any] = {"urls": []}
    for url in envelope.links:
        host = urlparse(url).hostname or ""
        item = {"url": url, "host": host}
        lower = url.lower()
        if any(lower.endswith(tld) or f"{tld}/" in lower for tld in SUSPICIOUS_TLDS):
            findings.append(f"suspicious tld: {host}")
            item["suspicious"] = True
        if "@" in urlparse(url).path:
            findings.append(f"credential-like path: {host}")
            item["suspicious"] = True
        # IP literal hosts
        if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host or ""):
            findings.append(f"ip-literal host: {host}")
            item["suspicious"] = True
        details["urls"].append(item)
    return StageResult(stage="C_url_intel", ok=True, findings=findings, details=details)


def _scan_bytes_for_malware(data: bytes | None, label: str) -> list[str]:
    findings: list[str] = []
    if data is None:
        return findings
    if EICAR in data or b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in data:
        findings.append(f"EICAR detected in {label}")
    # Lightweight YARA-like heuristics
    if re.search(rb"powershell\s+-enc", data, re.IGNORECASE):
        findings.append(f"encoded powershell in {label}")
    if re.search(rb"<script[\s>].*eval\(", data, re.IGNORECASE | re.DOTALL):
        findings.append(f"script eval pattern in {label}")
    return findings


def _stage_av_yara(
    envelope: ShieldEnvelope, cfg: ChannelShieldConfig, attachment_bytes: dict[str, bytes]
) -> StageResult:
    findings: list[str] = []
    details: dict[str, Any] = {"scanned": []}
    raw = None
    if envelope.raw_storage_uri.startswith("shield://raw/"):
        blob_id = envelope.raw_storage_uri.rsplit("/", 1)[-1]
        raw = read_raw_blob(cfg.raw_store_dir, blob_id)
        findings.extend(_scan_bytes_for_malware(raw, "raw"))
    for att in envelope.attachments:
        data = attachment_bytes.get(att.id)
        findings.extend(_scan_bytes_for_malware(data, att.filename))
        details["scanned"].append({"filename": att.filename, "sha256": att.sha256})
    # Optional ClamAV socket is best-effort; absence is not an error
    details["clamav_configured"] = bool(cfg.clamav_socket)
    details["yara_configured"] = bool(cfg.yara_rules_dir)
    malicious = any("EICAR" in f or "powershell" in f or "eval" in f for f in findings)
    return StageResult(
        stage="D_av_yara",
        ok=not malicious,
        findings=findings,
        details=details,
    )


def _stage_agent_triage(envelope: ShieldEnvelope) -> StageResult:
    """Redacted heuristic triage (no live LLM required for gateway)."""
    from keprix.channel_shield.redaction import redact_text

    findings: list[str] = []
    text = (envelope.text or "").lower()
    subject = (envelope.subject or "").lower()
    blob = f"{subject}\n{text}"
    for kw in PHISH_KEYWORDS:
        if kw in blob:
            findings.append(f"phish keyword: {kw}")
    if envelope.attachments:
        for att in envelope.attachments:
            ext = (att.extension or att.filename.rsplit(".", 1)[-1] if "." in att.filename else "").lower()
            if ext in {"exe", "scr", "js", "vbs", "hta", "iso"}:
                findings.append(f"risky attachment type: {att.filename}")
    redacted, reasons = redact_text(envelope.text or "")
    return StageResult(
        stage="E_agent_triage",
        ok=True,
        findings=findings,
        details={
            "redacted_preview": redacted[:120],
            "redaction_reasons": reasons,
        },
    )


def _needs_sandbox(att: ShieldAttachment, cfg: ChannelShieldConfig) -> bool:
    ext = (att.extension or "").lower().lstrip(".")
    if not ext and "." in att.filename:
        ext = att.filename.rsplit(".", 1)[-1].lower()
    return ext in set(cfg.sandbox_required_for)


def _stage_sandbox(
    envelope: ShieldEnvelope,
    cfg: ChannelShieldConfig,
    attachment_bytes: dict[str, bytes],
    *,
    sandbox_runner: Any | None = None,
) -> StageResult:
    findings: list[str] = []
    details: dict[str, Any] = {"sandboxed": []}
    for att in envelope.attachments:
        if not _needs_sandbox(att, cfg):
            continue
        data = attachment_bytes.get(att.id)
        result = {"filename": att.filename, "verdict": "clean"}
        if sandbox_runner is not None:
            try:
                out = sandbox_runner(att, data)
                result.update(out if isinstance(out, dict) else {"verdict": str(out)})
            except Exception as exc:
                findings.append(f"sandbox error: {att.filename}: {exc}")
                result["verdict"] = "error"
        else:
            # Built-in dry sandbox: flag EICAR / known bad
            bad = _scan_bytes_for_malware(data, att.filename)
            if bad:
                findings.extend([f"sandbox:{f}" for f in bad])
                result["verdict"] = "malicious"
            else:
                result["verdict"] = "clean"
        details["sandboxed"].append(result)
        if result.get("verdict") == "malicious":
            findings.append(f"sandbox malicious: {att.filename}")
        if result.get("verdict") == "error":
            findings.append(f"sandbox error: {att.filename}")
    return StageResult(stage="F_sandbox", ok=True, findings=findings, details=details)


def _decide_verdict(
    stages: list[StageResult], cfg: ChannelShieldConfig
) -> tuple[Verdict, list[str], float]:
    reasons: list[str] = []
    score = 0.0
    for stage in stages:
        if stage.stage == "A_parse" and not stage.ok:
            return Verdict.ERROR, stage.findings or ["parse failed"], 0.0
        for finding in stage.findings:
            reasons.append(f"{stage.stage}: {finding}")
            lower = finding.lower()
            if "eicar" in lower or "sandbox malicious" in lower or "powershell" in lower:
                score = max(score, 0.95)
            elif "spf=" in lower or "dkim=" in lower or "dmarc=" in lower:
                score = max(score, 0.55)
            elif "phish keyword" in lower or "suspicious tld" in lower:
                score = max(score, 0.65)
            elif "risky attachment" in lower or "ip-literal" in lower:
                score = max(score, 0.7)
            elif "sandbox error" in lower or "signature missing" in lower:
                score = max(score, 0.5 if not cfg.fail_closed_default else 0.9)
            else:
                score = max(score, 0.4)

    if score >= 0.9:
        return Verdict.MALICIOUS, reasons, score
    if score >= 0.5:
        return Verdict.SUSPECT, reasons, score
    if any(s.stage == "F_sandbox" and any("error" in f.lower() for f in s.findings) for s in stages):
        if cfg.fail_closed_default:
            return Verdict.ERROR, reasons or ["sandbox error fail-closed"], score
    return Verdict.CLEAN, reasons, score


def run_pipeline(
    envelope: ShieldEnvelope,
    *,
    cfg: ChannelShieldConfig | None = None,
    attachment_bytes: dict[str, bytes] | None = None,
    sandbox_runner: Any | None = None,
    message_id: str = "",
    raw_evidence_ref: str = "",
) -> PipelineReport:
    from keprix.channel_shield.agent_safe import build_agent_safe_content

    cfg = cfg or load_channel_shield_config()
    attachment_bytes = attachment_bytes or {}
    stages = [
        _stage_parse(envelope),
        _stage_identity(envelope),
        _stage_url_intel(envelope),
        _stage_av_yara(envelope, cfg, attachment_bytes),
        _stage_agent_triage(envelope),
        _stage_sandbox(envelope, cfg, attachment_bytes, sandbox_runner=sandbox_runner),
    ]
    verdict, reasons, score = _decide_verdict(stages, cfg)
    evidence_ref = raw_evidence_ref or envelope.raw_storage_uri or ""
    report = PipelineReport(
        verdict=verdict,
        stages=stages,
        reasons=reasons,
        threat_score=score,
        raw_evidence_ref=evidence_ref,
    )
    safe = build_agent_safe_content(
        envelope,
        report,
        message_id=message_id or envelope.external_message_id,
        raw_evidence_ref=evidence_ref,
    )
    report.agent_safe_content = safe.to_dict()
    report.policy_label = safe.policy_label.value
    return report
