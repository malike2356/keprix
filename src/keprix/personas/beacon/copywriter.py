"""Copy generation and brand voice enforcement for BEACON."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from keprix.compat import UTC
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix.personas.beacon.persona import BEACON_PERSONA
from keprix.workspace.document_helpers import word_count
from keprix.workspace.repository import workspace_repo

MARKETING_CLICHES = (
    "revolutionary",
    "game-changing",
    "game changing",
    "unprecedented",
    "disruptive",
    "cutting-edge",
    "cutting edge",
    "best-in-class",
    "world-class",
    "synergy",
    "leverage",
    "paradigm",
)

AI_TYPOGRAPHY_REPLACEMENTS = {
    "\u2014": ", ",
    "\u2013": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2026": "...",
}

COPY_TEMPLATES: dict[str, str] = {
    "landing_page": "# {headline}\n\n{subhead}\n\n## Why it matters\n\n{body}\n\n[Get started]({cta_url})",
    "email": "Subject: {subject}\n\nHi {name},\n\n{body}\n\n{signoff}",
    "social": "{hook}\n\n{body}\n\n{hashtags}",
    "ad": "{headline} | {body} | {cta}",
    "case_study": "# {title}\n\n**Client:** {client}\n\n## Challenge\n\n{challenge}\n\n## Result\n\n{result}",
}


@dataclass(slots=True)
class BrandVoice:
    client_name: str
    voice_summary: str
    formality: str = "professional"
    energy: str = "balanced"
    humor: str = "minimal"
    technical_depth: str = "moderate"
    preferred_terms: list[str] = field(default_factory=list)
    banned_terms: list[str] = field(default_factory=list)
    do_list: list[str] = field(default_factory=list)
    dont_list: list[str] = field(default_factory=list)
    example_phrases: list[str] = field(default_factory=list)
    reading_level_target: tuple[float, float] = (8.0, 10.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_name": self.client_name,
            "voice_summary": self.voice_summary,
            "formality": self.formality,
            "energy": self.energy,
            "humor": self.humor,
            "technical_depth": self.technical_depth,
            "preferred_terms": list(self.preferred_terms),
            "banned_terms": list(self.banned_terms),
            "do_list": list(self.do_list),
            "dont_list": list(self.dont_list),
            "example_phrases": list(self.example_phrases),
            "reading_level_target": list(self.reading_level_target),
        }

    def render_markdown(self) -> str:
        template_path = Path(__file__).resolve().parent / "prompts" / "brand_voice.md"
        template = template_path.read_text(encoding="utf-8")
        replacements = {
            "{{client_name}}": self.client_name,
            "{{version}}": "1.0",
            "{{updated_at}}": datetime.now(UTC).date().isoformat(),
            "{{voice_summary}}": self.voice_summary,
            "{{formality}}": self.formality,
            "{{energy}}": self.energy,
            "{{humor}}": self.humor,
            "{{technical_depth}}": self.technical_depth,
            "{{do_list}}": "\n".join(f"- {item}" for item in self.do_list) or "- Use clear, direct language",
            "{{dont_list}}": "\n".join(f"- {item}" for item in self.dont_list) or "- Avoid hype and cliches",
            "{{preferred_terms}}": ", ".join(self.preferred_terms) or "(none)",
            "{{banned_terms}}": ", ".join(self.banned_terms) or ", ".join(MARKETING_CLICHES[:5]),
            "{{example_phrases}}": "\n".join(f'- "{phrase}"' for phrase in self.example_phrases) or "- (add examples)",
        }
        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)
        return rendered


@dataclass(slots=True)
class CopyValidation:
    passed: bool
    issues: list[str] = field(default_factory=list)
    readability_grade: float = 0.0
    normalized_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "issues": list(self.issues),
            "readability_grade": self.readability_grade,
            "normalized_text": self.normalized_text,
        }


@dataclass
class CopyVariant:
    label: str
    content: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "content": self.content, "rationale": self.rationale}


@dataclass
class CopyResult:
    copy_id: str
    format_type: str
    content: str
    validation: CopyValidation
    variants: list[CopyVariant] = field(default_factory=list)
    word_count: int = 0
    reading_time_minutes: float = 0.0
    document_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "copy_id": self.copy_id,
            "format_type": self.format_type,
            "content": self.content,
            "validation": self.validation.to_dict(),
            "variants": [variant.to_dict() for variant in self.variants],
            "word_count": self.word_count,
            "reading_time_minutes": self.reading_time_minutes,
            "document_id": self.document_id,
        }


class BrandVoiceSetupRequired(Exception):
    """Raised when copy generation needs brand voice configuration first."""

    def __init__(self, prompt: dict[str, Any]) -> None:
        self.prompt = prompt
        super().__init__(prompt.get("message", "Brand voice required"))


class BeaconCopywriter:
    WORDS_PER_MINUTE = 200

    def __init__(self, *, workspace_id: str = "default", user_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = BEACON_PERSONA
        self._user = {"id": user_id, "username": user_id}
        self._brand_voices: dict[str, BrandVoice] = {}

    def _voice_key(self, client_id: str) -> str:
        return f"{self.workspace_id}:{client_id}"

    def save_brand_voice(self, client_id: str, voice: BrandVoice) -> dict[str, Any]:
        self._brand_voices[self._voice_key(client_id)] = voice
        doc = workspace_repo.create_document(
            self._user,
            title=f"Brand Voice: {voice.client_name}",
            content=voice.render_markdown(),
            tags=["beacon-brand-voice", f"client:{client_id}"],
        )
        return doc

    def load_brand_voice(self, client_id: str) -> BrandVoice | None:
        cached = self._brand_voices.get(self._voice_key(client_id))
        if cached:
            return cached
        docs = workspace_repo.list_documents(self._user, tag="beacon-brand-voice")
        for doc in docs:
            if f"client:{client_id}" in (doc.get("tags") or []):
                return BrandVoice(
                    client_name=client_id,
                    voice_summary=doc.get("content", "")[:240],
                )
        return None

    def brand_voice_setup_prompt(self, client_id: str) -> dict[str, Any]:
        return {
            "required": True,
            "client_id": client_id,
            "message": (
                "Before generating marketing copy, configure brand voice for this client. "
                "Share voice summary, tone, banned terms, and example phrases."
            ),
            "fields": [
                "client_name",
                "voice_summary",
                "formality",
                "energy",
                "banned_terms",
                "preferred_terms",
                "example_phrases",
            ],
        }

    def require_brand_voice(self, client_id: str) -> BrandVoice:
        voice = self.load_brand_voice(client_id)
        if voice is None:
            raise BrandVoiceSetupRequired(self.brand_voice_setup_prompt(client_id))
        return voice

    def normalize_typography(self, text: str) -> str:
        normalized = text
        for bad, good in AI_TYPOGRAPHY_REPLACEMENTS.items():
            normalized = normalized.replace(bad, good)
        return normalized

    def readability_grade(self, text: str) -> float:
        words = word_count(text)
        if words == 0:
            return 0.0
        sentences = max(1, len([part for part in re.split(r"[.!?]+", text) if part.strip()]))
        syllables = 0
        for token in text.split():
            syllables += max(1, len(re.findall(r"[aeiouy]+", token.lower())))
        asl = words / sentences
        asw = syllables / words
        return round(0.39 * asl + 11.8 * asw - 15.59, 1)

    def validate_copy(self, text: str, brand_voice: BrandVoice | None = None) -> CopyValidation:
        normalized = self.normalize_typography(text)
        issues: list[str] = []

        lowered = normalized.lower()
        for cliche in MARKETING_CLICHES:
            if cliche in lowered:
                issues.append(f"Cliche detected: {cliche}")

        if brand_voice:
            for term in brand_voice.banned_terms:
                if term.lower() in lowered:
                    issues.append(f"Banned term: {term}")

        for bad in AI_TYPOGRAPHY_REPLACEMENTS:
            if bad in text:
                issues.append("AI-typography artefact detected")

        grade = self.readability_grade(normalized)
        if brand_voice:
            low, high = brand_voice.reading_level_target
            if grade > high + 2:
                issues.append(f"Readability grade {grade} is too complex; target up to {high}")
            if grade < 4:
                issues.append(f"Readability grade {grade} is too simple for long-form content")

        unverified = re.findall(r"\b\d+%\b", normalized)
        aspirational_marked = "aspirational" in lowered or "goal:" in lowered
        if unverified and not aspirational_marked:
            issues.append("Numeric claims should be verifiable or marked aspirational")

        return CopyValidation(
            passed=not issues,
            issues=issues,
            readability_grade=grade,
            normalized_text=normalized,
        )

    def generate_copy(
        self,
        *,
        format_type: str,
        brief: dict[str, str],
        client_id: str = "default",
        store: bool = True,
        require_voice: bool = True,
    ) -> CopyResult:
        if require_voice:
            voice = self.require_brand_voice(client_id)
        else:
            voice = self.load_brand_voice(client_id)
            if voice is None:
                voice = BrandVoice(
                    client_name=client_id,
                    voice_summary="Clear, direct, professional marketing voice.",
                    dont_list=["Avoid hype and cliches"],
                )

        template = COPY_TEMPLATES.get(format_type, "{body}")
        merged = {
            "headline": brief.get("headline", brief.get("title", "Your headline here")),
            "subhead": brief.get("subhead", "A clear value proposition"),
            "body": brief.get("body", brief.get("message", "Explain the offer in plain language.")),
            "cta_url": brief.get("cta_url", "#"),
            "subject": brief.get("subject", brief.get("headline", "Update")),
            "name": brief.get("name", "there"),
            "signoff": brief.get("signoff", "The team"),
            "hook": brief.get("hook", brief.get("headline", "")),
            "hashtags": brief.get("hashtags", ""),
            "cta": brief.get("cta", "Learn more"),
            "title": brief.get("title", "Case study"),
            "client": brief.get("client", client_id),
            "challenge": brief.get("challenge", "Describe the challenge"),
            "result": brief.get("result", "Describe the measurable result"),
        }
        content = template.format(**merged)
        if voice.preferred_terms:
            content = f"{content}\n\n<!-- voice: {', '.join(voice.preferred_terms[:3])} -->"

        validation = self.validate_copy(content, voice)
        final_content = validation.normalized_text if validation.normalized_text else content
        words = word_count(final_content)
        reading_time = round(words / self.WORDS_PER_MINUTE, 1) if words else 0.0

        if words >= 300:
            final_content = (
                f"{final_content}\n\n---\nWord count: {words} | Reading time: {reading_time} min"
            )

        variants = self.generate_variants(final_content, voice)
        copy_id = str(uuid4())
        document_id = None
        if store:
            doc = workspace_repo.create_document(
                self._user,
                title=f"BEACON {format_type}: {merged['headline'][:60]}",
                content=final_content,
                tags=["beacon-copy", format_type, f"client:{client_id}"],
            )
            document_id = doc["id"]

        return CopyResult(
            copy_id=copy_id,
            format_type=format_type,
            content=final_content,
            validation=validation,
            variants=variants,
            word_count=words,
            reading_time_minutes=reading_time,
            document_id=document_id,
        )

    def generate_variants(self, base_content: str, brand_voice: BrandVoice | None = None) -> list[CopyVariant]:
        headline, _, rest = base_content.partition("\n")
        variants = [
            CopyVariant(
                label="A-direct",
                content=base_content,
                rationale="Direct benefit-led framing aligned to brand voice",
            ),
            CopyVariant(
                label="B-question",
                content=f"Need a better outcome?\n\n{rest or base_content}",
                rationale="Question hook to test engagement on cold audiences",
            ),
            CopyVariant(
                label="C-proof",
                content=f"{headline}\n\nTrusted by teams who need reliable results.\n\n{rest}".strip(),
                rationale="Social proof emphasis without unverified statistics",
            ),
        ]
        for variant in variants:
            validation = self.validate_copy(variant.content, brand_voice)
            variant.content = validation.normalized_text or variant.content
        return variants
