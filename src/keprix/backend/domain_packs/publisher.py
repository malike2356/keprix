"""Hub publication for domain packs (Prompt 30)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from keprix.backend.domain_packs.glossary import glossary_to_localization_payload
from keprix.backend.domain_packs.manifests import to_hub_manifest
from keprix.backend.domain_packs.schemas import DomainPackManifest
from keprix.backend.domain_packs.validation import validate_pack
from keprix.hub.installer import install_pack
from keprix.hub.registry import repo_packages_root


def publish_pack_dir(pack: DomainPackManifest) -> Path:
    slug = pack.domain_name.replace("_", "-").lower()
    root = repo_packages_root() / "packs" / slug
    root.mkdir(parents=True, exist_ok=True)

    (root / "pack.json").write_text(json.dumps(pack.to_dict(), indent=2), encoding="utf-8")
    (root / "glossary.json").write_text(json.dumps(glossary_to_localization_payload(pack), indent=2), encoding="utf-8")
    (root / "playbooks.json").write_text(json.dumps(pack.playbooks, indent=2), encoding="utf-8")
    (root / "schemas.json").write_text(json.dumps(pack.data_schemas, indent=2), encoding="utf-8")
    (root / "README.md").write_text(
        f"# {pack.domain_name} domain pack\n\nVersion {pack.version}\n",
        encoding="utf-8",
    )
    manifest = to_hub_manifest(pack)
    (root / "manifest.json").write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    return root


def publish_to_hub(pack: DomainPackManifest, *, approved: bool = False) -> dict[str, Any]:
    result = validate_pack(pack, for_publish=True)
    if not result.ok:
        return {"status": "error", "validation": result.to_dict()}
    if pack.review_required and pack.review_status != "approved" and not approved:
        return {
            "status": "awaiting_review",
            "message": "high-stakes domain pack requires human review approval",
            "validation": result.to_dict(),
        }

    pack_dir = publish_pack_dir(pack)
    manifest = to_hub_manifest(pack)
    install_result = install_pack(pack_dir, manifest, approved=True)
    pack.hub_published = install_result.get("status") == "installed"
    pack.status = "published" if pack.hub_published else pack.status
    return {
        "status": install_result.get("status"),
        "pack_dir": str(pack_dir),
        "install": install_result,
        "validation": result.to_dict(),
    }


def bump_version(pack: DomainPackManifest, new_version: str) -> DomainPackManifest:
    pack.version = new_version
    return pack


def remove_published_pack(pack: DomainPackManifest) -> None:
    slug = pack.domain_name.replace("_", "-").lower()
    root = repo_packages_root() / "packs" / slug
    if root.exists():
        shutil.rmtree(root)
