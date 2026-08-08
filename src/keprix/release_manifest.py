"""Canonical Keprix release identity and manifest validation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SCHEMA = "keprix.release-manifest.v1"
CHANNELS = {"stable", "beta", "development"}
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def installed_version() -> str:
    """Return the installed distribution version with a source-tree fallback."""
    try:
        return metadata.version("keprix")
    except metadata.PackageNotFoundError:
        from keprix_cli import __version__

        return __version__


def git_commit(root: Path | None = None) -> str:
    """Return the release commit without failing source archives."""
    override = os.getenv("KEPRIX_RELEASE_COMMIT", "").strip()
    if override:
        return override
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


@dataclass(frozen=True)
class ReleaseIdentity:
    version: str
    commit: str
    channel: str
    schema: str = SCHEMA

    def as_dict(self) -> dict[str, str]:
        return {
            "product": "Keprix",
            "version": self.version,
            "commit": self.commit,
            "channel": self.channel,
            "manifest_schema": self.schema,
        }


def current_identity(*, root: Path | None = None) -> ReleaseIdentity:
    channel = os.getenv("KEPRIX_RELEASE_CHANNEL", "development").strip().lower()
    if channel not in CHANNELS:
        channel = "development"
    return ReleaseIdentity(version=installed_version(), commit=git_commit(root), channel=channel)


def _immutable_https(url: str, *, channel: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return False
    lowered = parsed.path.lower()
    if channel == "stable" and ("/main/" in lowered or lowered.endswith("/latest")):
        return False
    return True


def validate_manifest(data: dict[str, Any]) -> list[str]:
    """Return deterministic validation errors for a release manifest."""
    errors: list[str] = []
    if data.get("schema") != SCHEMA:
        errors.append(f"schema must equal {SCHEMA}")
    version = str(data.get("version") or "")
    if not SEMVER.fullmatch(version):
        errors.append("version must be semantic versioning compatible")
    channel = str(data.get("channel") or "")
    if channel not in CHANNELS:
        errors.append("channel must be stable, beta, or development")
    commit = str(data.get("git_commit") or "")
    if commit != "unknown" and not re.fullmatch(r"[0-9a-f]{40}", commit):
        errors.append("git_commit must be a full lowercase SHA or unknown")
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("artifacts must be a list")
        artifacts = []
    seen: set[str] = set()
    for index, raw in enumerate(artifacts):
        prefix = f"artifacts[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{prefix} must be an object")
            continue
        artifact_id = str(raw.get("id") or "")
        if not artifact_id:
            errors.append(f"{prefix}.id is required")
        elif artifact_id in seen:
            errors.append(f"{prefix}.id must be unique")
        seen.add(artifact_id)
        if not _immutable_https(str(raw.get("url") or ""), channel=channel):
            errors.append(f"{prefix}.url must be immutable HTTPS")
        if not SHA256.fullmatch(str(raw.get("sha256") or "")):
            errors.append(f"{prefix}.sha256 must contain 64 lowercase hex characters")
        if not isinstance(raw.get("size"), int) or int(raw.get("size") or 0) < 1:
            errors.append(f"{prefix}.size must be a positive integer")
        for field in ("signature_url", "sbom_url", "provenance_url"):
            if not _immutable_https(str(raw.get(field) or ""), channel=channel):
                errors.append(f"{prefix}.{field} must be immutable HTTPS")
    return errors


def build_manifest(
    *,
    version: str,
    commit: str,
    tag: str,
    channel: str,
    artifacts: list[dict[str, Any]],
    built_at: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic manifest object and reject invalid input."""
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "product": "Keprix",
        "version": version,
        "git_commit": commit,
        "source_tag": tag,
        "channel": channel,
        "built_at": built_at or datetime.now(UTC).replace(microsecond=0).isoformat(),
        "compatibility": {
            "public_api": "v1",
            "sidecar_api": "v1",
            "database_schema": 10,
            "minimum_rollback_database_schema": 10,
        },
        "artifacts": sorted(artifacts, key=lambda item: str(item.get("id") or "")),
        "release_notes_url": f"https://github.com/malike2356/keprix/releases/tag/{tag}",
        "known_issues_url": "https://github.com/malike2356/keprix/issues",
        "support_url": "https://github.com/malike2356/keprix/discussions",
    }
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError("; ".join(errors))
    return manifest


def artifact_record(
    path: Path, *, base_url: str, kind: str, platform: str, arch: str
) -> dict[str, Any]:
    """Create the integrity fields for a release artifact on disk."""
    payload = path.read_bytes()
    url = f"{base_url.rstrip('/')}/{path.name}"
    return {
        "id": f"{kind}-{platform}-{arch}",
        "kind": kind,
        "platform": platform,
        "architecture": arch,
        "filename": path.name,
        "url": url,
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "signature_url": f"{url}.sig",
        "sbom_url": f"{url}.sbom.json",
        "provenance_url": f"{url}.intoto.jsonl",
        "required": True,
    }


def dumps(manifest: dict[str, Any]) -> str:
    """Serialize a manifest consistently for signing and comparison."""
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"
