"""Legal research and regulatory tracking for CODEX."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from keprix.personas.codex.persona import CODEX_PERSONA
from keprix.personas.codex.reviewer import LAWYER_REVIEW_WARNING, LEGAL_INFORMATION_DISCLAIMER
from keprix.personas.sage.researcher import SageResearcher
from keprix.workspace.repository import workspace_repo

OUT_OF_DEPTH_KEYWORDS = (
    "litigation strategy",
    "criminal",
    "court filing",
    "represent me in court",
    "file a lawsuit",
    "appeal grounds",
    "sentencing",
    "arrest",
    "prosecution",
    "case law analysis",
)

ADVICE_REQUEST_PATTERNS = (
    re.compile(r"\bshould i sign\b", re.I),
    re.compile(r"\bwhat should i do\b", re.I),
    re.compile(r"\bis it legal for me\b", re.I),
    re.compile(r"\bcan i sue\b", re.I),
    re.compile(r"\btell me whether to\b", re.I),
    re.compile(r"\bgive me legal advice\b", re.I),
)

UK_CHECKLISTS: dict[str, list[str]] = {
    "incorporation": [
        "Choose company structure (Ltd, LLP, etc.)",
        "Register with Companies House",
        "Appoint directors and identify PSCs",
        "Prepare articles of association and shareholder agreement",
        "Register for Corporation Tax with HMRC",
        "Open business bank account and record statutory registers",
    ],
    "data_protection": [
        "Identify lawful bases for processing under UK GDPR",
        "Publish a privacy notice covering rights and contact details",
        "Maintain records of processing activities (ROPA)",
        "Implement data breach response procedure (72-hour ICO consideration)",
        "Sign data processing agreements with processors",
        "Complete DPIA for high-risk processing",
    ],
    "employment_basics": [
        "Issue written statement of employment particulars",
        "Check right to work documentation",
        "Set pay, holiday, and working time policies",
        "Register as employer with HMRC for PAYE",
        "Maintain health and safety obligations",
        "Document disciplinary and grievance procedures",
    ],
}


@dataclass(slots=True)
class LegalAnswer:
    answer_id: str
    question: str
    jurisdiction: str
    information: str
    citations: list[str]
    disclaimer: str
    refused_advice: bool
    out_of_depth: bool
    specialist_referral: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer_id": self.answer_id,
            "question": self.question,
            "jurisdiction": self.jurisdiction,
            "information": self.information,
            "citations": list(self.citations),
            "disclaimer": self.disclaimer,
            "refused_advice": self.refused_advice,
            "out_of_depth": self.out_of_depth,
            "specialist_referral": self.specialist_referral,
        }


@dataclass
class RegulatoryUpdate:
    update_id: str
    topic: str
    jurisdiction: str
    summary: str
    implications: list[str]
    sources: list[str] = field(default_factory=list)
    checked_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "update_id": self.update_id,
            "topic": self.topic,
            "jurisdiction": self.jurisdiction,
            "summary": self.summary,
            "implications": list(self.implications),
            "sources": list(self.sources),
            "checked_at": self.checked_at,
        }


def is_advice_request(question: str) -> bool:
    return any(pattern.search(question) for pattern in ADVICE_REQUEST_PATTERNS)


def is_out_of_depth(question: str) -> bool:
    lowered = question.lower()
    return any(keyword in lowered for keyword in OUT_OF_DEPTH_KEYWORDS)


class CodexResearcher:
    def __init__(self, *, workspace_id: str = "default", user_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = CODEX_PERSONA
        self._user = {"id": user_id, "username": user_id}

    def answer_question(
        self,
        question: str,
        *,
        jurisdiction: str = "England and Wales (UK)",
    ) -> LegalAnswer:
        refused = is_advice_request(question)
        out_of_depth = is_out_of_depth(question)

        if out_of_depth:
            information = (
                f"This question appears to involve specialist legal work beyond CODEX's scope under {jurisdiction}. "
                "CODEX can share general information only; engage qualified counsel for litigation, criminal, or case-specific strategy."
            )
            referral = "Consult a specialist solicitor or barrister for your matter."
        elif refused:
            information = (
                "CODEX cannot tell you what you should do in your specific situation. "
                f"Under {jurisdiction} law, outcomes depend on facts, contract terms, and regulatory context. "
                "Below is general information to discuss with a lawyer."
            )
            referral = LAWYER_REVIEW_WARNING
        else:
            information = (
                f"General information ({jurisdiction}): many commercial agreements address this topic through "
                "contract terms, statutory minimums, and regulator guidance. Map the question to your documents and counsel."
            )
            referral = ""

        citations: list[str] = []
        if "gdpr" in question.lower() or "data protection" in question.lower():
            citations.append("UK GDPR / Data Protection Act 2018")
        if "employment" in question.lower() or "worker" in question.lower():
            citations.append("Employment Rights Act 1996 (UK)")
        if "company" in question.lower() or "incorporat" in question.lower():
            citations.append("Companies Act 2006 (UK)")

        return LegalAnswer(
            answer_id=str(uuid4()),
            question=question.strip(),
            jurisdiction=jurisdiction,
            information=information,
            citations=citations,
            disclaimer=LEGAL_INFORMATION_DISCLAIMER,
            refused_advice=refused,
            out_of_depth=out_of_depth,
            specialist_referral=referral,
        )

    def generate_checklist(self, checklist_type: str, *, jurisdiction: str = "England and Wales (UK)") -> dict[str, Any]:
        normalized = checklist_type.lower().replace(" ", "_")
        items = UK_CHECKLISTS.get(normalized)
        if items is None:
            items = [
                f"Confirm which {jurisdiction} statutes apply",
                "Gather existing contracts and policies",
                "Identify internal owners for compliance tasks",
                "Book review with qualified legal counsel",
            ]
        return {
            "checklist_type": normalized,
            "jurisdiction": jurisdiction,
            "items": items,
            "disclaimer": LEGAL_INFORMATION_DISCLAIMER,
        }

    async def track_regulatory_changes(
        self,
        topic: str,
        *,
        jurisdiction: str = "United Kingdom",
        use_research: bool = True,
        store: bool = True,
    ) -> RegulatoryUpdate:
        sources: list[str] = []
        summary = f"Regulatory scan for '{topic}' in {jurisdiction}."
        implications = [
            "Review whether existing policies reference current regulator guidance.",
            "Check contract templates for required clause updates.",
            "Schedule legal review if material compliance duties changed.",
        ]

        if use_research:
            researcher = SageResearcher(workspace_id=self.workspace_id, user_id=self.user_id)
            result = await researcher.research(
                f"{topic} regulatory changes {jurisdiction} legislation",
                index_to_rag=False,
                limit=3,
            )
            sources = [source.get("url", "") for source in result.sources if source.get("url")]
            if result.synthesis:
                summary = result.synthesis.split("\n")[0][:400]

        update = RegulatoryUpdate(
            update_id=str(uuid4()),
            topic=topic.strip(),
            jurisdiction=jurisdiction,
            summary=summary,
            implications=implications,
            sources=sources,
            checked_at=datetime.now(UTC).isoformat(),
        )

        if store:
            markdown = (
                f"# Regulatory update: {update.topic}\n\n"
                f"**Jurisdiction:** {update.jurisdiction}\n\n"
                f"{update.summary}\n\n"
                "## Implications\n"
                + "\n".join(f"- {item}" for item in update.implications)
                + f"\n\n{LEGAL_INFORMATION_DISCLAIMER}\n"
            )
            workspace_repo.create_document(
                self._user,
                title=f"Regulatory Update: {update.topic}",
                content=markdown,
                tags=["codex-regulatory", f"jurisdiction:{jurisdiction}"],
            )

        return update
