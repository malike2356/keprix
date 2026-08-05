"""Build agent-safe content and policy labels from pipeline verdicts."""

from __future__ import annotations

from typing import Any

from keprix.channel_shield.redaction import (
    extract_domains,
    redact_text,
    scrub_filename,
    scrub_url,
)
from keprix.channel_shield.types import (
    AgentSafeContent,
    MessageStatus,
    PipelineReport,
    PolicyLabel,
    ShieldEnvelope,
    Verdict,
)

BLOCKED_VERDICTS = {
    Verdict.MALICIOUS.value,
    Verdict.SUSPECT.value,
    Verdict.ERROR.value,
    "unknown_sender_high_risk",
}


def policy_label_for(
    verdict: Verdict | str,
    *,
    status: str | None = None,
) -> PolicyLabel:
    if status == MessageStatus.DESTROYED.value:
        return PolicyLabel.DESTROYED
    if status == MessageStatus.RELEASED.value:
        return PolicyLabel.CLEAN
    value = verdict.value if isinstance(verdict, Verdict) else str(verdict or "")
    if value == Verdict.CLEAN.value:
        return PolicyLabel.CLEAN
    if value == Verdict.SUSPECT.value:
        return PolicyLabel.NEEDS_HUMAN_REVIEW
    if value in {Verdict.MALICIOUS.value, "unknown_sender_high_risk"}:
        return PolicyLabel.BLOCKED
    if value == Verdict.ERROR.value:
        return PolicyLabel.SAFE_SUMMARY_ONLY
    if status == MessageStatus.QUARANTINED.value:
        return PolicyLabel.SAFE_SUMMARY_ONLY
    return PolicyLabel.NEEDS_HUMAN_REVIEW


def allowed_actions_for(
    label: PolicyLabel,
    *,
    released: bool = False,
) -> list[str]:
    if label == PolicyLabel.DESTROYED:
        return []
    if label == PolicyLabel.CLEAN or released:
        return [
            "view_safe_summary",
            "use_in_prompt",
            "write_incident_memory",
            "reply_externally_with_care",
        ]
    if label == PolicyLabel.NEEDS_HUMAN_REVIEW:
        return [
            "view_safe_summary",
            "request_release",
            "notify_security",
            "write_incident_memory",
        ]
    if label == PolicyLabel.SAFE_SUMMARY_ONLY:
        return ["view_safe_summary", "request_release", "write_incident_memory"]
    # blocked
    return ["view_safe_summary", "request_release", "request_destroy", "write_incident_memory"]


def build_agent_safe_content(
    envelope: ShieldEnvelope,
    report: PipelineReport,
    *,
    message_id: str,
    raw_evidence_ref: str,
    status: str | None = None,
) -> AgentSafeContent:
    redacted, redaction_reasons = redact_text(envelope.text or "")
    subject_safe, subject_reasons = redact_text(envelope.subject or "")
    redaction_reasons = list(dict.fromkeys(redaction_reasons + subject_reasons))
    domains = extract_domains(envelope.text or "", envelope.links)
    domain_safe = [scrub_url(f"https://{d}/") for d in domains]
    attachment_meta = [
        {
            "id": att.id,
            "filename": scrub_filename(att.filename),
            "contentType": att.content_type,
            "size": att.size,
            "sha256": att.sha256,
            "extension": att.extension,
        }
        for att in envelope.attachments
    ]
    label = policy_label_for(report.verdict, status=status)
    actions = allowed_actions_for(
        label,
        released=status == MessageStatus.RELEASED.value,
    )
    preview = redacted[:280]
    return AgentSafeContent(
        policy_label=label,
        text=redacted if label == PolicyLabel.CLEAN else preview,
        subject=subject_safe,
        domains=domains,
        domain_labels=domain_safe,
        attachment_metadata=attachment_meta,
        verdict=report.verdict.value,
        confidence=round(report.threat_score, 3),
        reasons=list(report.reasons)[:20],
        redaction_reasons=redaction_reasons,
        allowed_actions=actions,
        provenance={
            "channel": envelope.channel,
            "protectionId": envelope.protection_id,
            "externalMessageId": envelope.external_message_id,
            "messageId": message_id,
            "from": envelope.from_addr,
        },
        raw_evidence_ref=raw_evidence_ref,
    )


def agent_safe_dict(content: AgentSafeContent) -> dict[str, Any]:
    return content.to_dict()
