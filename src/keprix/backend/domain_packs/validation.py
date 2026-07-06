"""Domain pack validation orchestrator (Prompt 30)."""

from __future__ import annotations

from dataclasses import dataclass, field

from keprix.backend.domain_packs.glossary import validate_glossary
from keprix.backend.domain_packs.jurisdiction import is_regulated_domain, validate_jurisdictions
from keprix.backend.domain_packs.localization import validate_localization_metadata
from keprix.backend.domain_packs.playbooks import validate_playbooks
from keprix.backend.domain_packs.schemas import DomainPackManifest
from keprix.backend.domain_packs.source_quality import compute_pack_quality_score, source_quality_errors


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}


def validate_pack(pack: DomainPackManifest, *, for_publish: bool = False) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not pack.domain_name.strip():
        errors.append("domain_name is required")
    if not pack.version.strip():
        errors.append("version is required")

    errors.extend(validate_jurisdictions(pack))
    errors.extend(source_quality_errors(pack))
    errors.extend(validate_glossary(pack))
    errors.extend(validate_playbooks(pack))
    errors.extend(validate_localization_metadata(pack))

    if not pack.disclaimers:
        errors.append("at least one disclaimer is required")
    if not pack.limitations:
        errors.append("limitations list is required")
    if not pack.can_do:
        warnings.append("can_do list is empty")
    if not pack.cannot_do:
        warnings.append("cannot_do list is empty")

    if is_regulated_domain(pack.domain_name):
        pack.review_required = True
        if not pack.disclaimers:
            errors.append("high-stakes domain requires disclaimer")
        if pack.review_status not in {"approved", "pending"}:
            if for_publish:
                errors.append("high-stakes domain requires human review before publish")
        if not pack.cannot_do:
            errors.append("high-stakes domain must state what it cannot do")

    pack.source_quality_score = compute_pack_quality_score(pack)
    if pack.source_quality_score < 0.6 and for_publish:
        warnings.append("source quality score below recommended threshold (0.6)")

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)
