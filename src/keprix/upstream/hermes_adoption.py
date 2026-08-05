"""Generate numbered adoption prompts from tracked Hermes features."""

from __future__ import annotations

import re
from pathlib import Path

from keprix.upstream.hermes_monitor import (
    APPROVED_FOR_ADOPT,
    AdoptionStatus,
    HermesMonitor,
    UpstreamFeature,
    default_prompts_dir,
)
from keprix.upstream.work_package import build_work_package


class AdoptionPromptGenerator:
    """Render adoption prompts and update inventory state."""

    def __init__(
        self,
        monitor: HermesMonitor,
        *,
        prompts_dir: str | Path | None = None,
        template_path: str | Path | None = None,
        work_packages_dir: str | Path | None = None,
    ) -> None:
        self.monitor = monitor
        self.prompts_dir = Path(prompts_dir or default_prompts_dir())
        self.work_packages_dir = Path(work_packages_dir) if work_packages_dir else None
        template = template_path or Path(__file__).resolve().parent / "templates" / "adoption_prompt.md"
        self.template = template.read_text(encoding="utf-8")

    def generate(self, feature_id: str, *, require_approval: bool = True) -> Path:
        feature = self.monitor.get_feature(feature_id)
        if feature is None:
            raise KeyError(f"Unknown upstream feature: {feature_id}")

        if require_approval:
            if not feature.is_decided:
                raise PermissionError(
                    f"Feature {feature_id} is pending review. "
                    f"Run `keprix upstream decide {feature_id} --status adopt_with_hardening` first."
                )
            if feature.adoption_status.value not in APPROVED_FOR_ADOPT:
                raise PermissionError(
                    f"Feature {feature_id} status is {feature.adoption_status.value}; "
                    "adopt only works for adopt / adopt_with_hardening."
                )

        prompt_number = int(self.monitor.inventory.get("next_prompt_number") or 290)
        slug = self._slugify(feature.name)
        filename = f"{prompt_number}-adopt-hermes-{slug}.md"
        output_path = self.prompts_dir / filename

        content = self._render(feature, prompt_number)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

        work_path = build_work_package(
            feature,
            prompt_path=output_path,
            output_dir=self.work_packages_dir,
        )

        feature.adoption_prompt_id = f"prompt-{prompt_number}"
        feature.work_package_path = str(work_path)
        tracked = dict(self.monitor.inventory.get("tracked_features") or {})
        tracked[feature.feature_id] = feature.to_dict()
        self.monitor.inventory["tracked_features"] = tracked
        self.monitor.inventory["next_prompt_number"] = prompt_number + 1
        self.monitor._save_inventory()

        self._emit_adopted_signal(feature, prompt_number, output_path)
        return output_path

    def _render(self, feature: UpstreamFeature, prompt_number: int) -> str:
        security_lines = "\n".join(f"- {line}" for line in feature.security_implications) or "- None identified"
        implementation = self._implementation_notes(feature)
        hardening = self._hardening_notes(feature)
        enrichment = []
        if feature.compare_summary:
            enrichment.append(f"- **Compare:** {feature.compare_summary}")
        if feature.changelog_refs:
            enrichment.append("- **CHANGELOG hits:**")
            enrichment.extend(f"  - {line}" for line in feature.changelog_refs)
        if feature.triage_notes:
            enrichment.append(f"- **Triage:** {feature.triage_notes}")
        enrichment_block = "\n".join(enrichment) if enrichment else "- None"
        return self.template.format(
            prompt_number=prompt_number,
            feature_name=feature.name,
            version=feature.version_introduced,
            release_date=feature.release_date,
            release_url=feature.release_url,
            category=feature.category.value,
            description=feature.description,
            security_assessment=security_lines,
            implementation_notes=implementation,
            hardening_notes=hardening,
            enrichment=enrichment_block,
        )

    def _implementation_notes(self, feature: UpstreamFeature) -> str:
        if feature.keprix_equivalent:
            return (
                f"Keprix may already cover this via `{feature.keprix_equivalent}`. "
                "Confirm parity, then close or narrow scope before building."
            )
        return (
            f"Port the Hermes capability into Keprix with the same operator workflow, "
            f"using Keprix tool/provider/routing abstractions for `{feature.category.value}` features. "
            "Do not merge Hermes git diffs; rebuild against Keprix modules."
        )

    def _hardening_notes(self, feature: UpstreamFeature) -> str:
        if feature.adoption_status == AdoptionStatus.ADOPT_WITH_HARDENING:
            return (
                "Ship with sandbox policy, governance rules, egress allowlist updates, "
                "prompt guard scanning, and Scout signal emission before enabling by default."
            )
        if feature.adoption_status == AdoptionStatus.SKIP:
            return "No hardening required; feature is out of scope for Keprix."
        return (
            "Review security implications above and add hardening where the feature "
            "touches tools, network, memory, or credentials."
        )

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug[:60] or "feature"

    def _emit_adopted_signal(
        self,
        feature: UpstreamFeature,
        prompt_number: int,
        output_path: Path,
    ) -> None:
        try:
            from keprix.security.scout_integration import emit_scout_signal
            from keprix.security.scout_types import SignalCategory, SignalSeverity

            emit_scout_signal(
                SignalCategory.GOVERNANCE,
                SignalSeverity.INFO,
                "upstream.feature_adopted",
                feature.feature_id,
                {
                    "prompt_number": prompt_number,
                    "prompt_path": str(output_path),
                    "work_package_path": feature.work_package_path,
                    "category": feature.category.value,
                    "adoption_status": feature.adoption_status.value,
                    "security_implications": feature.security_implications,
                },
            )
        except Exception:
            pass
