"""Document drafting and jurisdiction templates for CODEX."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from keprix.compat import UTC
from typing import Any
from uuid import uuid4

from keprix.personas.codex.persona import CODEX_PERSONA
from keprix.personas.codex.reviewer import LAWYER_REVIEW_WARNING, LEGAL_INFORMATION_DISCLAIMER
from keprix.workspace.repository import workspace_repo

UK_STANDARD_CLAUSES = (
    "parties_and_definitions",
    "scope_or_services",
    "fees_and_payment",
    "term_and_termination",
    "confidentiality",
    "intellectual_property",
    "data_protection_uk_gdpr",
    "limitation_of_liability",
    "indemnity",
    "governing_law_england_wales",
    "dispute_resolution",
    "notices",
    "entire_agreement",
    "amendments",
)

DOCUMENT_TEMPLATES: dict[str, list[str]] = {
    "nda": list(UK_STANDARD_CLAUSES[:6]) + ["return_of_information", "governing_law_england_wales"],
    "service_agreement": list(UK_STANDARD_CLAUSES),
    "terms_of_service": [
        "acceptance",
        "services_description",
        "user_obligations",
        "fees",
        "intellectual_property",
        "acceptable_use",
        "limitation_of_liability",
        "termination",
        "privacy_reference",
        "governing_law_england_wales",
    ],
    "privacy_policy": [
        "controller_identity",
        "data_collected",
        "lawful_bases_uk_gdpr",
        "retention",
        "recipients_and_processors",
        "international_transfers",
        "data_subject_rights",
        "cookies",
        "contact_and_complaints",
        "updates",
    ],
    "contractor_agreement": [
        "status_as_contractor",
        "services_and_deliverables",
        "fees_and_invoicing",
        "confidentiality",
        "intellectual_property",
        "data_protection_uk_gdpr",
        "insurance",
        "termination",
        "limitation_of_liability",
        "governing_law_england_wales",
    ],
}


@dataclass
class DraftDocument:
    draft_id: str
    document_type: str
    title: str
    jurisdiction: str
    parties: dict[str, str]
    clauses_included: list[str]
    content: str
    disclaimer: str = LEGAL_INFORMATION_DISCLAIMER
    lawyer_warning: str = LAWYER_REVIEW_WARNING
    document_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "document_type": self.document_type,
            "title": self.title,
            "jurisdiction": self.jurisdiction,
            "parties": dict(self.parties),
            "clauses_included": list(self.clauses_included),
            "content": self.content,
            "disclaimer": self.disclaimer,
            "lawyer_warning": self.lawyer_warning,
            "document_id": self.document_id,
        }


class CodexDrafter:
    def __init__(self, *, workspace_id: str = "default", user_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = CODEX_PERSONA
        self._user = {"id": user_id, "username": user_id}
        self._clause_library = self.persona.prompts_dir / "clause_library.md"

    def supported_document_types(self) -> list[str]:
        return sorted(DOCUMENT_TEMPLATES)

    def clauses_for_type(self, document_type: str, *, jurisdiction: str) -> list[str]:
        normalized = document_type.lower().replace(" ", "_")
        clauses = list(DOCUMENT_TEMPLATES.get(normalized, UK_STANDARD_CLAUSES))
        if jurisdiction.lower().startswith("uk") or "england" in jurisdiction.lower():
            if "governing_law_england_wales" not in clauses:
                clauses.append("governing_law_england_wales")
        return clauses

    def render_clause_section(self, clause_key: str, *, parties: dict[str, str], jurisdiction: str) -> str:
        party_a = parties.get("party_a", "Party A")
        party_b = parties.get("party_b", "Party B")
        templates = {
            "parties_and_definitions": f"1. **Parties.** This agreement is between {party_a} and {party_b}.\n",
            "scope_or_services": "2. **Scope.** The supplier will provide the services described in Schedule 1.\n",
            "fees_and_payment": "3. **Fees.** Fees, invoicing, and payment terms are set out in Schedule 2.\n",
            "term_and_termination": "4. **Term.** Either party may terminate on 30 days' written notice unless otherwise stated.\n",
            "confidentiality": "5. **Confidentiality.** Each party will protect the other's confidential information.\n",
            "intellectual_property": "6. **IP.** Pre-existing IP remains with its owner; deliverable IP is assigned as stated.\n",
            "data_protection_uk_gdpr": (
                f"7. **Data protection ({jurisdiction}).** Parties will comply with UK GDPR and agree processor terms where applicable.\n"
            ),
            "limitation_of_liability": "8. **Liability cap.** Liability is capped at fees paid in the prior 12 months, excluding fraud or wilful misconduct.\n",
            "indemnity": "9. **Indemnity.** Mutual indemnities apply for third-party IP infringement caused by breach.\n",
            "governing_law_england_wales": f"10. **Governing law.** This agreement is governed by the laws of {jurisdiction}.\n",
            "dispute_resolution": "11. **Disputes.** Parties will attempt good-faith negotiation before court proceedings.\n",
            "notices": "12. **Notices.** Formal notices must be sent to the addresses in Schedule 3.\n",
            "entire_agreement": "13. **Entire agreement.** This document supersedes prior discussions on the same subject.\n",
            "amendments": "14. **Amendments.** Changes must be in writing and signed by both parties.\n",
            "acceptance": "1. **Acceptance.** By using the service, users accept these terms.\n",
            "controller_identity": f"1. **Controller.** {party_a} is the data controller for personal data described here.\n",
            "lawful_bases_uk_gdpr": "2. **Lawful bases.** Processing relies on contract, legitimate interests, and consent where required.\n",
            "status_as_contractor": f"1. **Status.** {party_b} is an independent contractor, not an employee.\n",
        }
        return templates.get(clause_key, f"- **{clause_key.replace('_', ' ').title()}.** [Draft clause placeholder]\n")

    def draft_document(
        self,
        *,
        document_type: str,
        title: str,
        jurisdiction: str = "England and Wales (UK)",
        parties: dict[str, str] | None = None,
        store: bool = True,
    ) -> DraftDocument:
        normalized = document_type.lower().replace(" ", "_")
        if normalized not in DOCUMENT_TEMPLATES:
            raise ValueError(f"Unsupported document type: {document_type}")

        party_data = parties or {"party_a": "Company Ltd", "party_b": "Counterparty Ltd"}
        clauses = self.clauses_for_type(normalized, jurisdiction=jurisdiction)

        sections = [
            f"# {title}",
            "",
            f"**Jurisdiction:** {jurisdiction}",
            f"**Draft ID:** {uuid4()}",
            f"**Date:** {datetime.now(UTC).date().isoformat()}",
            "",
            "## Draft clauses",
            "",
        ]
        for clause in clauses:
            sections.append(self.render_clause_section(clause, parties=party_data, jurisdiction=jurisdiction))

        sections.extend(
            [
                "",
                "## Disclaimer",
                "",
                LEGAL_INFORMATION_DISCLAIMER,
                "",
                f"WARNING: {LAWYER_REVIEW_WARNING}",
            ]
        )
        content = "\n".join(sections)

        draft = DraftDocument(
            draft_id=str(uuid4()),
            document_type=normalized,
            title=title,
            jurisdiction=jurisdiction,
            parties=party_data,
            clauses_included=clauses,
            content=content,
        )

        if store:
            doc = workspace_repo.create_document(
                self._user,
                title=f"Draft: {title}",
                content=content,
                tags=["codex-draft", normalized, f"jurisdiction:{jurisdiction}"],
            )
            draft.document_id = doc.get("id")

        return draft
