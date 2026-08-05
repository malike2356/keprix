"""Monitor Hermes Agent upstream releases and evaluate Keprix adoption."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import httpx
import yaml
from packaging.version import Version

from keprix.upstream.capability_registry import load_capability_map, match_capability
from keprix.upstream.inventory_store import (
    BUNDLED_INVENTORY_PATH,
    default_inventory_path,
    ensure_runtime_inventory,
)

logger = logging.getLogger(__name__)

PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_PROMPTS_DIR = PACKAGE_ROOT.parents[3] / "1st-plan" / "1st-prompt" / "pending-prompts"

APPROVED_FOR_ADOPT = frozenset({"adopt", "adopt_with_hardening"})
DECISION_STATUSES = frozenset(
    {
        "already_have",
        "adopt",
        "adopt_with_hardening",
        "skip",
        "defer",
        "blocked",
    }
)


class FeatureCategory(str, Enum):
    TOOL = "tool"
    PROVIDER = "provider"
    ROUTING = "routing"
    MEMORY = "memory"
    COMPRESSION = "compression"
    UI_CLI = "ui_cli"
    PLATFORM = "platform"
    SECURITY = "security"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    OTHER = "other"


class AdoptionStatus(str, Enum):
    UNEVALUATED = "unevaluated"
    ALREADY_HAVE = "already_have"
    ADOPT = "adopt"
    ADOPT_WITH_HARDENING = "adopt_with_hardening"
    SKIP = "skip"
    DEFER = "defer"
    BLOCKED = "blocked"


@dataclass
class UpstreamFeature:
    feature_id: str
    name: str
    description: str
    category: FeatureCategory
    version_introduced: str
    release_date: str
    release_url: str
    adoption_status: AdoptionStatus = AdoptionStatus.UNEVALUATED
    suggested_status: AdoptionStatus | None = None
    adoption_prompt_id: str | None = None
    security_implications: list[str] = field(default_factory=list)
    keprix_equivalent: str | None = None
    notes: str = ""
    decided_by: str | None = None
    decided_at: str | None = None
    decision_notes: str = ""
    changelog_refs: list[str] = field(default_factory=list)
    compare_summary: str = ""
    triage_notes: str = ""
    work_package_path: str | None = None

    @property
    def is_decided(self) -> bool:
        return bool(self.decided_at) and self.adoption_status != AdoptionStatus.UNEVALUATED

    @property
    def can_adopt(self) -> bool:
        return (
            self.is_decided
            and self.adoption_status.value in APPROVED_FOR_ADOPT
            and not self.adoption_prompt_id
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["category"] = self.category.value
        payload["adoption_status"] = self.adoption_status.value
        payload["suggested_status"] = (
            self.suggested_status.value if self.suggested_status else None
        )
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> UpstreamFeature:
        suggested_raw = payload.get("suggested_status")
        suggested = AdoptionStatus(str(suggested_raw)) if suggested_raw else None
        return cls(
            feature_id=str(payload["feature_id"]),
            name=str(payload.get("name") or ""),
            description=str(payload.get("description") or ""),
            category=FeatureCategory(str(payload.get("category") or FeatureCategory.OTHER.value)),
            version_introduced=str(payload.get("version_introduced") or "0.0.0"),
            release_date=str(payload.get("release_date") or ""),
            release_url=str(payload.get("release_url") or ""),
            adoption_status=AdoptionStatus(
                str(payload.get("adoption_status") or AdoptionStatus.UNEVALUATED.value)
            ),
            suggested_status=suggested,
            adoption_prompt_id=payload.get("adoption_prompt_id"),
            security_implications=list(payload.get("security_implications") or []),
            keprix_equivalent=payload.get("keprix_equivalent"),
            notes=str(payload.get("notes") or ""),
            decided_by=payload.get("decided_by"),
            decided_at=payload.get("decided_at"),
            decision_notes=str(payload.get("decision_notes") or ""),
            changelog_refs=list(payload.get("changelog_refs") or []),
            compare_summary=str(payload.get("compare_summary") or ""),
            triage_notes=str(payload.get("triage_notes") or ""),
            work_package_path=payload.get("work_package_path"),
        )


def default_prompts_dir() -> Path:
    return DEFAULT_PROMPTS_DIR


def _parse_release_datetime(value: str) -> datetime:
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw).astimezone(timezone.utc)


def _stable_feature_id(version: Version, feature_text: str) -> str:
    digest = hashlib.sha256(f"{version}:{feature_text}".encode("utf-8")).hexdigest()[:8]
    return f"hermes-{version}-{digest}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class HermesMonitor:
    """Monitors Hermes upstream and tracks feature adoption state."""

    GITHUB_API = "https://api.github.com/repos/NousResearch/hermes-agent/releases"
    GITHUB_CHANGELOG = (
        "https://raw.githubusercontent.com/NousResearch/hermes-agent/main/CHANGELOG.md"
    )
    GITHUB_COMPARE = "https://api.github.com/repos/NousResearch/hermes-agent/compare"
    PYPI_API = "https://pypi.org/pypi/hermes-agent/json"
    CHECK_INTERVAL_HOURS = 24

    def __init__(self, inventory_path: str | Path | None = None) -> None:
        if inventory_path is None:
            self.inventory_path = default_inventory_path()
        else:
            self.inventory_path = Path(inventory_path)
        self.inventory: dict[str, Any] = self._load_inventory()
        self._ensure_keprix_features()
        self.keprix_version = self._get_keprix_version()

    def _ensure_keprix_features(self) -> None:
        caps = load_capability_map()
        existing = dict(self.inventory.get("keprix_features") or {})
        if len(existing) < len(caps):
            existing.update(caps)
            self.inventory["keprix_features"] = existing

    async def check(self, *, emit_scout: bool = True, fetch_enrichment: bool = True) -> list[UpstreamFeature]:
        releases = await self._fetch_releases()
        pypi_version = await self._fetch_pypi_version()
        if pypi_version:
            self.inventory["pypi_last_version"] = str(pypi_version)

        changelog_text = ""
        if fetch_enrichment:
            changelog_text = await self._fetch_changelog()

        new_features: list[UpstreamFeature] = []
        processed = set(self.inventory.get("processed_versions") or [])
        tracked: dict[str, Any] = dict(self.inventory.get("tracked_features") or {})
        previous_versions = sorted(processed, key=Version) if processed else []

        for release in releases:
            tag = str(release.get("tag_name") or "").lstrip("v")
            if not tag:
                continue
            try:
                version = Version(tag)
            except Exception:
                continue
            if str(version) in processed:
                continue

            compare_summary = ""
            if fetch_enrichment and previous_versions:
                base = previous_versions[-1]
                compare_summary = await self._fetch_compare_summary(base, str(version))

            features = self._parse_release_notes(release)
            for feature in features:
                suggested = self._evaluate_adoption(feature)
                feature.suggested_status = suggested
                feature.security_implications = self._assess_security(feature)
                if changelog_text:
                    feature.changelog_refs = self._changelog_hits(changelog_text, feature)
                if compare_summary:
                    feature.compare_summary = compare_summary
                feature.triage_notes = self._build_triage_notes(feature)
                try:
                    from keprix.upstream.llm_triage import maybe_llm_triage

                    llm_extra = maybe_llm_triage(feature)
                    if llm_extra:
                        feature.triage_notes = f"{feature.triage_notes} LLM: {llm_extra}"
                except Exception:
                    pass

                if suggested == AdoptionStatus.ALREADY_HAVE:
                    feature.adoption_status = AdoptionStatus.ALREADY_HAVE
                    feature.decided_by = "system"
                    feature.decided_at = _now_iso()
                    feature.decision_notes = "Auto-matched to Keprix capability registry."
                else:
                    # Human approval required before adopt/skip/defer/blocked.
                    feature.adoption_status = AdoptionStatus.UNEVALUATED

                tracked[feature.feature_id] = feature.to_dict()
                new_features.append(feature)

            processed.add(str(version))
            previous_versions = sorted(processed, key=Version)
            if emit_scout:
                self._emit_release_signal(version, features, release)

        self.inventory["processed_versions"] = sorted(processed, key=Version)
        self.inventory["tracked_features"] = tracked
        self.inventory["last_check"] = _now_iso()
        self._save_inventory()
        return new_features

    async def _fetch_releases(self) -> list[dict[str, Any]]:
        releases: list[dict[str, Any]] = []
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "keprix-upstream-monitor"}
        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            response = await client.get(self.GITHUB_API)
            if response.status_code == 200:
                payload = response.json()
                if isinstance(payload, list):
                    releases.extend(payload)
            else:
                logger.warning("GitHub releases fetch failed status=%s", response.status_code)
        return releases

    async def _fetch_pypi_version(self) -> Version | None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(self.PYPI_API)
            if response.status_code != 200:
                return None
            info = response.json().get("info") or {}
            version = info.get("version")
            if not version:
                return None
            return Version(str(version))

    async def _fetch_changelog(self) -> str:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.GITHUB_CHANGELOG)
                if response.status_code == 200:
                    return response.text
        except Exception:
            logger.debug("changelog fetch failed", exc_info=True)
        return ""

    async def _fetch_compare_summary(self, base: str, head: str) -> str:
        url = f"{self.GITHUB_COMPARE}/{base}...v{head}"
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "keprix-upstream-monitor"}
        try:
            async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    # Retry without v prefix on head
                    response = await client.get(f"{self.GITHUB_COMPARE}/{base}...{head}")
                if response.status_code != 200:
                    return ""
                payload = response.json()
                files = payload.get("files") or []
                commits = payload.get("commits") or []
                top_files = [
                    str(row.get("filename") or "")
                    for row in files[:12]
                    if row.get("filename")
                ]
                commit_msgs = [
                    str((row.get("commit") or {}).get("message") or "").split("\n", 1)[0][:80]
                    for row in commits[:8]
                ]
                parts = [
                    f"compare {base}...{head}: {len(commits)} commits, {len(files)} files",
                ]
                if top_files:
                    parts.append("files: " + ", ".join(top_files))
                if commit_msgs:
                    parts.append("commits: " + " | ".join(commit_msgs))
                return "; ".join(parts)
        except Exception:
            logger.debug("compare fetch failed", exc_info=True)
            return ""

    def _changelog_hits(self, changelog: str, feature: UpstreamFeature) -> list[str]:
        hits: list[str] = []
        version_header = re.compile(
            rf"^##+\s*\[?v?{re.escape(feature.version_introduced)}\]?.*$",
            re.IGNORECASE | re.MULTILINE,
        )
        match = version_header.search(changelog)
        snippet = changelog
        if match:
            start = match.start()
            next_header = re.search(r"^##+\s+", changelog[match.end() :], re.MULTILINE)
            end = match.end() + (next_header.start() if next_header else 800)
            snippet = changelog[start:end]
        keywords = [w for w in re.findall(r"[A-Za-z]{4,}", feature.description.lower())][:6]
        for line in snippet.splitlines():
            lower = line.lower()
            if any(word in lower for word in keywords):
                cleaned = line.strip()
                if cleaned and cleaned not in hits:
                    hits.append(cleaned[:200])
            if len(hits) >= 5:
                break
        return hits

    def _build_triage_notes(self, feature: UpstreamFeature) -> str:
        """Deterministic triage assist (no LLM required). Optional LLM can append later."""
        suggested = feature.suggested_status.value if feature.suggested_status else "unevaluated"
        bits = [
            f"Suggested status: {suggested}.",
            f"Category: {feature.category.value}.",
        ]
        if feature.keprix_equivalent:
            bits.append(f"Possible Keprix equivalent: {feature.keprix_equivalent}.")
        if feature.security_implications:
            bits.append(f"Security flags: {len(feature.security_implications)}.")
        if feature.compare_summary:
            bits.append("GitHub compare summary attached.")
        if feature.changelog_refs:
            bits.append(f"CHANGELOG hits: {len(feature.changelog_refs)}.")
        bits.append("Human decision required before adopt.")
        return " ".join(bits)

    def _parse_release_notes(self, release: dict[str, Any]) -> list[UpstreamFeature]:
        body = str(release.get("body") or "")
        version = Version(str(release.get("tag_name") or "0").lstrip("v"))
        published = str(release.get("published_at") or datetime.now(timezone.utc).isoformat())
        release_date = _parse_release_datetime(published).isoformat().replace("+00:00", "Z")
        release_url = str(release.get("html_url") or "")
        features: list[UpstreamFeature] = []

        for section in body.split("## "):
            if not section.strip():
                continue
            lines = section.split("\n")
            section_title = lines[0].strip().lower()
            for line in lines[1:]:
                stripped = line.strip()
                if not (stripped.startswith("- ") or stripped.startswith("* ")):
                    continue
                feature_text = stripped[2:].strip()
                if len(feature_text) <= 10:
                    continue
                category = self._categorise(feature_text, section_title)
                features.append(
                    UpstreamFeature(
                        feature_id=_stable_feature_id(version, feature_text),
                        name=feature_text[:100],
                        description=feature_text,
                        category=category,
                        version_introduced=str(version),
                        release_date=release_date,
                        release_url=release_url,
                    )
                )
        return features

    def _categorise(self, text: str, section: str) -> FeatureCategory:
        text_lower = text.lower()
        section_lower = section.lower()

        if any(word in text_lower for word in ("tool", "mcp", "execute", "browser")):
            return FeatureCategory.TOOL
        if any(word in text_lower for word in ("provider", "model", "openai", "anthropic")):
            return FeatureCategory.PROVIDER
        if any(word in text_lower for word in ("routing", "fallback", "combo", "quota")):
            return FeatureCategory.ROUTING
        if any(word in text_lower for word in ("memory", "workspace", "session", "persist")):
            return FeatureCategory.MEMORY
        if any(word in text_lower for word in ("compress", "token", "context")):
            return FeatureCategory.COMPRESSION
        if any(word in text_lower for word in ("cli", "tui", "dashboard", " ui")):
            return FeatureCategory.UI_CLI
        if any(word in text_lower for word in ("android", "ios", "mobile", "desktop", "platform")):
            return FeatureCategory.PLATFORM
        if any(word in text_lower for word in ("security", "sandbox", "auth", "encrypt")):
            return FeatureCategory.SECURITY
        if any(word in text_lower for word in ("integration", "webhook", "plugin")):
            return FeatureCategory.INTEGRATION
        if any(word in text_lower for word in ("performance", "speed", "cache", "faster")):
            return FeatureCategory.PERFORMANCE
        if "security" in section_lower:
            return FeatureCategory.SECURITY
        return FeatureCategory.OTHER

    def _evaluate_adoption(self, feature: UpstreamFeature) -> AdoptionStatus:
        """Return suggested status only; does not write final adoption_status."""
        # Prefer explicit inventory / prompt entries for hard already_have.
        for existing_id, existing_desc in (self.inventory.get("keprix_features") or {}).items():
            if str(existing_id).startswith("cap:") or str(existing_id) in load_capability_map():
                continue
            if self._is_equivalent(feature, str(existing_desc)):
                feature.keprix_equivalent = existing_id
                return AdoptionStatus.ALREADY_HAVE

        # Capability registry is a soft hint; only auto-close on very strong overlap.
        cap_id, score = match_capability(feature.description)
        if cap_id and score >= 0.35:
            feature.keprix_equivalent = cap_id
            if score >= 0.7:
                return AdoptionStatus.ALREADY_HAVE

        always_adopt = {
            FeatureCategory.TOOL,
            FeatureCategory.PROVIDER,
            FeatureCategory.ROUTING,
            FeatureCategory.COMPRESSION,
        }
        if feature.category in always_adopt:
            return AdoptionStatus.ADOPT_WITH_HARDENING

        evaluate = {
            FeatureCategory.MEMORY,
            FeatureCategory.INTEGRATION,
            FeatureCategory.PERFORMANCE,
            FeatureCategory.UI_CLI,
            FeatureCategory.SECURITY,
            FeatureCategory.OTHER,
        }
        if feature.category in evaluate:
            return AdoptionStatus.UNEVALUATED

        skip = {FeatureCategory.PLATFORM}
        if feature.category in skip:
            return AdoptionStatus.SKIP

        return AdoptionStatus.UNEVALUATED

    def _assess_security(self, feature: UpstreamFeature) -> list[str]:
        implications: list[str] = []
        if feature.category == FeatureCategory.TOOL:
            implications.extend(
                [
                    "New tool = new attack surface. Must pass through sandbox + governance.",
                    "Add to tool policy: allowlist/blocklist, rate limits, confirmation rules.",
                    "Emit Scout signals for tool invocation.",
                ]
            )
        if feature.category == FeatureCategory.PROVIDER:
            implications.extend(
                [
                    "New provider = new API key. Must go into credential vault, not env/config.",
                    "Provider must be added to egress filter domain allowlist.",
                    "Test for SSRF; provider endpoints can be spoofed.",
                ]
            )
        if feature.category == FeatureCategory.MEMORY:
            implications.extend(
                [
                    "Memory is a persistence vector. Scan writes with MEM-001 through MEM-007.",
                    "Memory content scanner must run before every write.",
                    "Memory content can be poisoned across sessions; threat pattern scan required.",
                ]
            )
        if feature.category == FeatureCategory.INTEGRATION:
            implications.extend(
                [
                    "Third-party integration = supply chain risk.",
                    "Skills guard must scan integration code before loading.",
                    "Add integration domains to egress filter allowlist.",
                ]
            )
        if feature.category == FeatureCategory.COMPRESSION:
            implications.extend(
                [
                    "Compression can hide injection payloads. Decompress before scanning.",
                    "Input sanitizer must run on decompressed content, not compressed.",
                ]
            )
        return implications

    def _is_equivalent(self, feature: UpstreamFeature, existing_desc: str) -> bool:
        def _words(text: str) -> set[str]:
            cleaned = []
            for token in text.lower().split():
                cleaned.append("".join(ch for ch in token if ch.isalnum()))
            return {word for word in cleaned if len(word) > 2}

        feature_words = _words(feature.description)
        existing_words = _words(existing_desc)
        if not feature_words:
            return False
        overlap = feature_words & existing_words
        return len(overlap) / max(len(feature_words), 1) > 0.5

    def list_features(
        self,
        *,
        category: str | None = None,
        status: str | None = None,
        pending_only: bool = False,
    ) -> list[UpstreamFeature]:
        tracked = self.inventory.get("tracked_features") or {}
        features = [UpstreamFeature.from_dict(row) for row in tracked.values()]
        if category:
            features = [feature for feature in features if feature.category.value == category]
        if status:
            features = [feature for feature in features if feature.adoption_status.value == status]
        if pending_only:
            features = [feature for feature in features if not feature.is_decided]
        return sorted(features, key=lambda item: (item.version_introduced, item.feature_id))

    def get_feature(self, feature_id: str) -> UpstreamFeature | None:
        row = (self.inventory.get("tracked_features") or {}).get(feature_id)
        if not row:
            return None
        return UpstreamFeature.from_dict(row)

    def decide(
        self,
        feature_id: str,
        status: str,
        *,
        decided_by: str = "operator",
        notes: str = "",
        keprix_equivalent: str | None = None,
    ) -> UpstreamFeature:
        feature = self.get_feature(feature_id)
        if feature is None:
            raise KeyError(f"Unknown upstream feature: {feature_id}")
        status_key = status.strip().lower().replace("-", "_")
        if status_key not in DECISION_STATUSES:
            raise ValueError(
                f"Invalid decision status '{status}'. "
                f"Allowed: {', '.join(sorted(DECISION_STATUSES))}"
            )
        feature.adoption_status = AdoptionStatus(status_key)
        feature.decided_by = decided_by
        feature.decided_at = _now_iso()
        feature.decision_notes = notes
        if keprix_equivalent:
            feature.keprix_equivalent = keprix_equivalent
        self._persist_feature(feature)
        self._emit_decision_signal(feature)
        return feature

    def mark_complete(
        self,
        feature_id: str,
        *,
        keprix_equivalent: str,
        notes: str = "",
        decided_by: str = "operator",
    ) -> UpstreamFeature:
        feature = self.get_feature(feature_id)
        if feature is None:
            raise KeyError(f"Unknown upstream feature: {feature_id}")
        feature.adoption_status = AdoptionStatus.ALREADY_HAVE
        feature.keprix_equivalent = keprix_equivalent
        feature.decided_by = decided_by
        feature.decided_at = _now_iso()
        feature.decision_notes = notes or "Adoption implemented and verified."
        caps = dict(self.inventory.get("keprix_features") or {})
        caps[keprix_equivalent] = feature.description
        self.inventory["keprix_features"] = caps
        self._persist_feature(feature)
        return feature

    def _persist_feature(self, feature: UpstreamFeature) -> None:
        tracked = dict(self.inventory.get("tracked_features") or {})
        tracked[feature.feature_id] = feature.to_dict()
        self.inventory["tracked_features"] = tracked
        self._save_inventory()

    def feature_diff(self) -> dict[str, Any]:
        keprix_features = self.inventory.get("keprix_features") or {}
        tracked = self.list_features()
        pending = [feature for feature in tracked if not feature.is_decided]
        adoptable = [
            feature
            for feature in tracked
            if feature.adoption_status.value in APPROVED_FOR_ADOPT and feature.is_decided
        ]
        return {
            "keprix_prompt_count": len(keprix_features),
            "tracked_hermes_features": len(tracked),
            "pending_review": len(pending),
            "adoptable_features": len(adoptable),
            "processed_versions": list(self.inventory.get("processed_versions") or []),
            "pypi_last_version": self.inventory.get("pypi_last_version"),
            "keprix_version": str(self.keprix_version),
            "inventory_path": str(self.inventory_path),
        }

    def report(self) -> dict[str, Any]:
        tracked = self.list_features()
        by_status: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for feature in tracked:
            by_status[feature.adoption_status.value] = by_status.get(feature.adoption_status.value, 0) + 1
            by_category[feature.category.value] = by_category.get(feature.category.value, 0) + 1
        return {
            "generated_at": _now_iso(),
            "last_check": self.inventory.get("last_check"),
            "processed_versions": len(self.inventory.get("processed_versions") or []),
            "keprix_features": len(self.inventory.get("keprix_features") or {}),
            "next_prompt_number": self.inventory.get("next_prompt_number", 290),
            "tracked_features": len(tracked),
            "pending_review": len([f for f in tracked if not f.is_decided]),
            "by_status": by_status,
            "by_category": by_category,
            "diff": self.feature_diff(),
            "inventory_path": str(self.inventory_path),
        }

    def _emit_release_signal(
        self,
        version: Version,
        features: list[UpstreamFeature],
        release: dict[str, Any],
    ) -> None:
        try:
            from keprix.security.scout_integration import emit_scout_signal
            from keprix.security.scout_types import SignalCategory, SignalSeverity

            emit_scout_signal(
                SignalCategory.GOVERNANCE,
                SignalSeverity.INFO,
                "upstream.new_release",
                f"hermes:{version}",
                {
                    "version": str(version),
                    "feature_count": len(features),
                    "release_url": release.get("html_url"),
                    "pending_review": sum(
                        1 for feature in features if feature.adoption_status == AdoptionStatus.UNEVALUATED
                    ),
                },
            )
        except Exception:
            logger.debug("upstream scout signal skipped", exc_info=True)

    def _emit_decision_signal(self, feature: UpstreamFeature) -> None:
        try:
            from keprix.security.scout_integration import emit_scout_signal
            from keprix.security.scout_types import SignalCategory, SignalSeverity

            emit_scout_signal(
                SignalCategory.GOVERNANCE,
                SignalSeverity.INFO,
                "upstream.feature_decided",
                feature.feature_id,
                {
                    "status": feature.adoption_status.value,
                    "decided_by": feature.decided_by,
                    "category": feature.category.value,
                },
            )
        except Exception:
            logger.debug("upstream decision signal skipped", exc_info=True)

    def _load_inventory(self) -> dict[str, Any]:
        if self.inventory_path.exists():
            with self.inventory_path.open(encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
        if BUNDLED_INVENTORY_PATH.exists() and self.inventory_path != BUNDLED_INVENTORY_PATH:
            with BUNDLED_INVENTORY_PATH.open(encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
        return {
            "processed_versions": [],
            "keprix_features": {},
            "tracked_features": {},
            "last_check": None,
            "next_prompt_number": 290,
        }

    def _save_inventory(self) -> None:
        self.inventory_path.parent.mkdir(parents=True, exist_ok=True)
        with self.inventory_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(self.inventory, handle, default_flow_style=False, sort_keys=False)

    def _get_keprix_version(self) -> Version:
        try:
            from keprix.config.constants import PRODUCT_VERSION

            return Version(PRODUCT_VERSION)
        except Exception:
            try:
                from keprix_cli import __version__

                return Version(__version__)
            except Exception:
                return Version("0.1.0")

    def to_json(self, features: list[UpstreamFeature]) -> str:
        return json.dumps([feature.to_dict() for feature in features], indent=2)


# Re-export for callers that imported ensure from monitor historically
__all__ = [
    "APPROVED_FOR_ADOPT",
    "AdoptionStatus",
    "FeatureCategory",
    "HermesMonitor",
    "UpstreamFeature",
    "default_inventory_path",
    "default_prompts_dir",
    "ensure_runtime_inventory",
]
