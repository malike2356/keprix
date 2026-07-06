"""Client deliverable production and review for BEACON."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from keprix.backend.localization.schemas import TranslationResult
from keprix.personas.beacon.copywriter import BeaconCopywriter
from keprix.personas.beacon.persona import BEACON_PERSONA
from keprix.workspace.document_helpers import export_document, word_count
from keprix.workspace.repository import workspace_repo


@dataclass(slots=True)
class DeliveryReview:
    passed: bool
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "issues": list(self.issues)}


@dataclass
class DeliverablePackage:
    deliverable_id: str
    title: str
    format: str
    content: str | bytes
    mime_type: str
    review: DeliveryReview
    document_id: str | None = None
    localized: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        content_value: str | bytes = self.content
        if isinstance(content_value, bytes):
            content_value = f"<binary {len(content_value)} bytes>"
        return {
            "deliverable_id": self.deliverable_id,
            "title": self.title,
            "format": self.format,
            "content": content_value,
            "mime_type": self.mime_type,
            "review": self.review.to_dict(),
            "document_id": self.document_id,
            "localized": dict(self.localized),
        }


class BeaconDelivery:
    def __init__(self, *, workspace_id: str = "default", user_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = BEACON_PERSONA
        self._user = {"id": user_id, "username": user_id}
        self._copywriter = BeaconCopywriter(workspace_id=workspace_id, user_id=user_id)

    def review_deliverable(self, content: str, *, client_id: str = "default") -> DeliveryReview:
        voice = self._copywriter.load_brand_voice(client_id)
        validation = self._copywriter.validate_copy(content, voice)
        issues = list(validation.issues)
        if word_count(content) < 20:
            issues.append("Deliverable content is too short for client delivery")
        return DeliveryReview(passed=not issues, issues=issues)

    def _slides_markdown(self, title: str, content: str) -> str:
        sections = [part.strip() for part in content.split("\n## ") if part.strip()]
        slides = [f"# {title}", ""]
        for index, section in enumerate(sections, start=1):
            slides.append(f"---\n\n## Slide {index}\n\n{section}")
        return "\n".join(slides)

    async def localize_content(self, content: str, target_language: str) -> TranslationResult:
        if target_language in {"en", "en-US", "en-GB", "en-GH"}:
            return TranslationResult(
                source_language="en",
                target_language=target_language,
                source_text=content,
                translated_text=content,
                confidence=1.0,
                glossary_matches=[],
                warnings=[],
                provider="passthrough",
            )
        from keprix.backend.localization.translation import translate_text

        return await translate_text(
            workspace_id=self.workspace_id,
            text=content,
            source_language="en",
            target_language=target_language,
            user_id=self.user_id,
        )

    async def prepare_deliverable(
        self,
        *,
        title: str,
        content: str,
        output_format: str = "pdf",
        client_id: str = "default",
        target_languages: list[str] | None = None,
        store: bool = True,
    ) -> DeliverablePackage:
        from uuid import uuid4

        review = self.review_deliverable(content, client_id=client_id)
        normalized = self._copywriter.normalize_typography(content)

        if output_format == "slides":
            payload = self._slides_markdown(title, normalized)
            mime_type = "text/markdown; charset=utf-8"
        elif output_format == "pdf":
            mime_type, payload = export_document({"title": title, "content": normalized}, "pdf")
        elif output_format == "html":
            mime_type, payload = export_document({"title": title, "content": normalized}, "html")
        else:
            mime_type, payload = export_document({"title": title, "content": normalized}, "markdown")

        localized: dict[str, str] = {}
        for language in target_languages or []:
            result = await self.localize_content(normalized, language)
            localized[language] = result.translated_text

        document_id = None
        if store:
            doc = workspace_repo.create_document(
                self._user,
                title=title,
                content=normalized if isinstance(payload, str) else normalized,
                tags=["beacon-deliverable", output_format, f"client:{client_id}"],
            )
            document_id = doc["id"]

        return DeliverablePackage(
            deliverable_id=str(uuid4()),
            title=title,
            format=output_format,
            content=payload,
            mime_type=mime_type,
            review=review,
            document_id=document_id,
            localized=localized,
        )
