"""Contract review and clause analysis for CODEX."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from keprix.memory.rag.indexer import RagIndexer
from keprix.personas.codex.persona import CODEX_PERSONA
from keprix.personas.warden.auditor import WardenAuditor
from keprix.workspace.repository import workspace_repo

LEGAL_INFORMATION_DISCLAIMER = (
    "This is legal information, not legal advice. Consult a qualified lawyer for your specific situation."
)
LAWYER_REVIEW_WARNING = "A qualified lawyer should review this before you sign."


class RiskLevel(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


CLAUSE_DETECTORS: list[tuple[str, re.Pattern[str], RiskLevel, str]] = [
    (
        "Limitation of Liability",
        re.compile(r"limitation of liability|liability.{0,40}limited|cap.{0,20}liability", re.I),
        RiskLevel.MEDIUM,
        "Check whether liability caps are mutual and whether consequential losses are excluded fairly.",
    ),
    (
        "Unlimited Liability",
        re.compile(r"unlimited liability|without limit|no limit on liability", re.I),
        RiskLevel.HIGH,
        "Uncapped liability exposure can be material; negotiate a reasonable cap.",
    ),
    (
        "Indemnity",
        re.compile(r"\bindemnif(y|ies|ication)\b", re.I),
        RiskLevel.MEDIUM,
        "Indemnities can shift significant risk; check scope, triggers, and whether they are mutual.",
    ),
    (
        "Termination",
        re.compile(r"\bterminat(e|ion|ed)\b", re.I),
        RiskLevel.LOW,
        "Review notice periods, fees on exit, and data return obligations.",
    ),
    (
        "Governing Law",
        re.compile(r"governing law|law of england|law of wales|jurisdiction", re.I),
        RiskLevel.LOW,
        "Confirm the chosen law and courts are practical for your business.",
    ),
    (
        "Data Protection",
        re.compile(r"personal data|data protection|processor|controller|gdpr|uk gdpr", re.I),
        RiskLevel.MEDIUM,
        "Processor terms, breach notification, and subprocessor controls should be explicit.",
    ),
    (
        "Intellectual Property",
        re.compile(r"intellectual property|\bip rights\b|work product|assignment of", re.I),
        RiskLevel.MEDIUM,
        "Clarify ownership of deliverables and licences to background IP.",
    ),
    (
        "Non-Compete",
        re.compile(r"non[- ]compete|non[- ]solicit|restraint of trade", re.I),
        RiskLevel.HIGH,
        "Restrictive covenants may be hard to enforce if scope or duration is excessive.",
    ),
    (
        "Auto-Renewal",
        re.compile(r"auto[- ]?renew|automatically renew|rolling term", re.I),
        RiskLevel.MEDIUM,
        "Watch renewal notice windows and price change mechanics.",
    ),
    (
        "Assignment",
        re.compile(r"\bassign(ment|able|ed)?\b", re.I),
        RiskLevel.LOW,
        "Check whether assignment requires consent and if change-of-control is covered.",
    ),
    (
        "Confidentiality",
        re.compile(r"confidential(ity)?|non[- ]disclosure", re.I),
        RiskLevel.LOW,
        "Confirm mutual obligations and how long confidentiality survives termination.",
    ),
]

MISSING_PROTECTION_CHECKS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "Limitation of liability cap",
        re.compile(r"limitation of liability|liability.{0,40}limited", re.I),
        "Add a mutual liability cap appropriate to contract value.",
    ),
    (
        "Data breach notification",
        re.compile(r"breach notification|security incident|notify.{0,30}breach", re.I),
        "Require prompt breach notification and cooperation timelines.",
    ),
    (
        "Termination for convenience",
        re.compile(r"terminat(e|ion).{0,40}convenience", re.I),
        "Include reasonable termination for convenience with notice.",
    ),
    (
        "IP ownership of deliverables",
        re.compile(r"intellectual property|work product|ownership of deliverables", re.I),
        "State who owns deliverables and what licence is granted.",
    ),
]

SECURITY_CLAUSE_CHECKS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "encryption_at_rest",
        re.compile(r"encrypt(ed|ion)?.{0,40}(data|information)", re.I),
        "Confirm encryption standards for stored personal data.",
    ),
    (
        "subprocessors",
        re.compile(r"sub[- ]?processor|subcontractor.{0,30}data", re.I),
        "Subprocessor approval and flow-down obligations should be documented.",
    ),
    (
        "audit_rights",
        re.compile(r"audit rights|security audit|inspect.{0,20}controls", re.I),
        "Audit and assurance rights help verify security commitments.",
    ),
]


@dataclass(slots=True)
class ClauseFinding:
    name: str
    explanation: str
    risk: str
    rationale: str
    suggested_revision: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "explanation": self.explanation,
            "risk": self.risk,
            "rationale": self.rationale,
            "suggested_revision": self.suggested_revision,
        }


@dataclass
class ContractReview:
    review_id: str
    title: str
    jurisdiction: str
    date_reviewed: str
    summary: str
    key_clauses: list[ClauseFinding] = field(default_factory=list)
    missing_protections: list[str] = field(default_factory=list)
    recommended_revisions: list[str] = field(default_factory=list)
    security_notes: list[str] = field(default_factory=list)
    bottom_line: str = ""
    disclaimer: str = LEGAL_INFORMATION_DISCLAIMER
    lawyer_warning: str = LAWYER_REVIEW_WARNING
    document_id: str | None = None
    markdown: str = ""
    indexed_chunks: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "title": self.title,
            "jurisdiction": self.jurisdiction,
            "date_reviewed": self.date_reviewed,
            "summary": self.summary,
            "key_clauses": [clause.to_dict() for clause in self.key_clauses],
            "missing_protections": list(self.missing_protections),
            "recommended_revisions": list(self.recommended_revisions),
            "security_notes": list(self.security_notes),
            "bottom_line": self.bottom_line,
            "disclaimer": self.disclaimer,
            "lawyer_warning": self.lawyer_warning,
            "document_id": self.document_id,
            "markdown": self.markdown,
            "indexed_chunks": self.indexed_chunks,
        }


def score_clause_risk(name: str, text: str) -> RiskLevel:
    lowered = text.lower()
    if name == "Unlimited Liability" or "unlimited liability" in lowered:
        return RiskLevel.HIGH
    if name in {"Non-Compete", "Unlimited Liability"}:
        return RiskLevel.HIGH
    if name in {"Indemnity", "Data Protection", "Intellectual Property", "Auto-Renewal"}:
        if any(marker in lowered for marker in ("solely", "one-way", "unilateral", "all losses", "any and all")):
            return RiskLevel.HIGH
        return RiskLevel.MEDIUM
    if name == "Limitation of Liability" and re.search(r"unlimited|no cap", lowered):
        return RiskLevel.HIGH
    return RiskLevel.LOW if name in {"Termination", "Governing Law", "Assignment", "Confidentiality"} else RiskLevel.MEDIUM


def extract_clause_snippet(text: str, pattern: re.Pattern[str], *, window: int = 120) -> str:
    match = pattern.search(text)
    if not match:
        return ""
    start = max(0, match.start() - 40)
    end = min(len(text), match.end() + window)
    snippet = text[start:end].strip()
    return re.sub(r"\s+", " ", snippet)


def analyze_contract_text(text: str, *, jurisdiction: str) -> tuple[list[ClauseFinding], list[str], list[str], list[str]]:
    findings: list[ClauseFinding] = []
    seen: set[str] = set()

    for name, pattern, default_risk, rationale in CLAUSE_DETECTORS:
        if not pattern.search(text):
            continue
        if name in seen:
            continue
        seen.add(name)
        snippet = extract_clause_snippet(text, pattern)
        risk = score_clause_risk(name, snippet or text)
        revision = ""
        if risk == RiskLevel.HIGH:
            revision = f"Negotiate narrower language for '{name}' and align with {jurisdiction} market norms."
        elif risk == RiskLevel.MEDIUM:
            revision = f"Clarify scope and mutuality for '{name}'."
        findings.append(
            ClauseFinding(
                name=name,
                explanation=snippet or f"The agreement addresses {name.lower()}.",
                risk=risk,
                rationale=rationale,
                suggested_revision=revision,
            )
        )

    missing: list[str] = []
    revisions: list[str] = []
    for label, pattern, recommendation in MISSING_PROTECTION_CHECKS:
        if not pattern.search(text):
            missing.append(label)
            revisions.append(recommendation)

    security_notes: list[str] = []
    for label, pattern, note in SECURITY_CLAUSE_CHECKS:
        if pattern.search(text):
            security_notes.append(f"{label}: {note}")
        elif label in {"subprocessors", "audit_rights"} and re.search(r"personal data|processor", text, re.I):
            missing.append(f"{label.replace('_', ' ')} (security)")
            revisions.append(note)
            security_notes.append(f"Missing {label}: {note}")

    findings.sort(key=lambda row: {RiskLevel.HIGH: 3, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 1}[RiskLevel(row.risk)], reverse=True)
    return findings, missing, revisions, security_notes


class CodexReviewer:
    def __init__(self, *, workspace_id: str = "default", user_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = CODEX_PERSONA
        self._user = {"id": user_id, "username": user_id}
        self._template_path = self.persona.prompts_dir / "review_template.md"
        self._clause_library_path = self.persona.prompts_dir / "clause_library.md"
        self._indexer = RagIndexer()
        self._warden = WardenAuditor(workspace_id=workspace_id)

    def scan_with_warden(self, contract_text: str) -> list[str]:
        notes: list[str] = []
        if re.search(r"personal data|processor|subprocessor", contract_text, re.I):
            audit = self._warden.run_audit(
                request="Review contract security and privacy clauses",
                content_samples=[contract_text[:4000]],
            )
            for finding in audit.findings:
                if finding.category in {"secrets", "privacy", "general"}:
                    notes.append(f"{finding.severity}: {finding.message}")
        return notes[:5]

    async def index_clause_library(self) -> int:
        content = self._clause_library_path.read_text(encoding="utf-8")
        metadata = f"<!-- codex-clause-library jurisdiction=multi indexed_at={datetime.now(UTC).isoformat()} -->\n"
        return await self._indexer.ingest(
            user_id=self.user_id,
            source_type="codex_clause_library",
            source_id="clause-library",
            content=metadata + content,
        )

    def render_review(self, review: ContractReview) -> str:
        template = self._template_path.read_text(encoding="utf-8")
        clause_lines = []
        for clause in review.key_clauses:
            clause_lines.append(
                f"- {clause.name}; {clause.explanation[:200]}; RISK: {clause.risk}\n  {clause.rationale}"
            )
        return (
            template.replace("{{title}}", review.title)
            .replace("{{jurisdiction}}", review.jurisdiction)
            .replace("{{date_reviewed}}", review.date_reviewed)
            .replace("{{summary}}", review.summary)
            .replace("{{key_clauses}}", "\n".join(clause_lines) or "- None detected")
            .replace("{{missing_protections}}", "\n".join(f"- {item}" for item in review.missing_protections) or "- None flagged")
            .replace(
                "{{recommended_revisions}}",
                "\n".join(f"- {item}" for item in review.recommended_revisions) or "- None suggested",
            )
            .replace(
                "{{security_notes}}",
                "\n".join(f"- {item}" for item in review.security_notes) or "- No additional security notes",
            )
            .replace("{{bottom_line}}", review.bottom_line)
            .replace("{{disclaimer}}", review.disclaimer)
        )

    async def review_contract(
        self,
        *,
        title: str,
        text: str,
        jurisdiction: str = "England and Wales (UK)",
        store: bool = True,
        index_to_rag: bool = True,
    ) -> ContractReview:
        review_id = str(uuid4())
        date_reviewed = datetime.now(UTC).date().isoformat()

        clauses, missing, revisions, security_notes = analyze_contract_text(text, jurisdiction=jurisdiction)
        warden_notes = self.scan_with_warden(text)
        security_notes = list(dict.fromkeys([*security_notes, *warden_notes]))

        high_risk = sum(1 for clause in clauses if clause.risk == RiskLevel.HIGH)
        summary = (
            f"This document appears to be a commercial agreement reviewed under {jurisdiction}. "
            f"CODEX identified {len(clauses)} key clause area(s), including {high_risk} higher-risk item(s)."
        )
        if high_risk:
            bottom_line = (
                "Several higher-risk clauses warrant negotiation before signing. "
                "Use the recommended revisions as a starting point for lawyer-led markup."
            )
        else:
            bottom_line = (
                "No critical red flags detected by automated review, but manual lawyer review is still essential "
                "before you rely on or sign this document."
            )

        review = ContractReview(
            review_id=review_id,
            title=title,
            jurisdiction=jurisdiction,
            date_reviewed=date_reviewed,
            summary=summary,
            key_clauses=clauses,
            missing_protections=missing,
            recommended_revisions=revisions,
            security_notes=security_notes,
            bottom_line=bottom_line,
        )
        review.markdown = self.render_review(review)
        review.markdown += f"\n\nWARNING: {LAWYER_REVIEW_WARNING}\n"

        if store:
            doc = workspace_repo.create_document(
                self._user,
                title=f"Contract Review: {title}",
                content=review.markdown,
                tags=["codex-review", f"jurisdiction:{jurisdiction}"],
            )
            review.document_id = doc.get("id")

        if index_to_rag:
            review.indexed_chunks = await self._indexer.ingest(
                user_id=self.user_id,
                source_type="codex_contract_review",
                source_id=review_id,
                content=review.markdown,
            )

        return review
