"""Load product keprix.yaml manifests for upgrade operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .check import UpgradeManifestInfo


@dataclass
class ProductManifest:
    """Parsed keprix.yaml for a Keprix-based product."""
    product_name: str
    product_slug: str
    product_version: str
    keprix_min_version: str
    keprix_tested_against: str
    keprix_incompatible_with: list[str] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    path: Path = field(default_factory=Path)

    def to_upgrade_info(self) -> UpgradeManifestInfo:
        return UpgradeManifestInfo(
            product_name=self.product_name,
            keprix_tested_against=self.keprix_tested_against,
            keprix_min_version=self.keprix_min_version,
            keprix_incompatible_with=list(self.keprix_incompatible_with),
        )


def default_ce_manifest(root: Path) -> ProductManifest:
    """Fallback manifest when running Keprix CE without a product keprix.yaml."""
    from importlib import metadata

    try:
        installed = metadata.version("keprix")
    except metadata.PackageNotFoundError:
        from keprix_cli import __version__

        installed = __version__
    return ProductManifest(
        product_name="Keprix",
        product_slug="keprix",
        product_version=installed,
        keprix_min_version="0.1.0",
        keprix_tested_against=installed,
        keprix_incompatible_with=[],
        features={},
        raw={
            "product": {"name": "Keprix", "slug": "keprix", "version": installed},
            "keprix": {"min_version": "0.1.0", "tested_against": installed},
            "features": {},
        },
        path=root / "keprix.yaml",
    )


def load_product_manifest(manifest_path: Path) -> ProductManifest:
    """Load and validate a product manifest from keprix.yaml."""
    path = manifest_path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid manifest format in {path}")

    product = data.get("product") or {}
    keprix = data.get("keprix") or {}
    if not isinstance(product, dict):
        product = {}
    if not isinstance(keprix, dict):
        keprix = {}

    name = str(product.get("name") or product.get("display_name") or path.parent.name)
    slug = str(product.get("slug") or name.lower().replace(" ", "-"))
    product_version = str(product.get("version") or "0.0.0")
    min_version = str(keprix.get("min_version") or "0.1.0")
    tested_against = str(keprix.get("tested_against") or min_version)
    incompatible = keprix.get("incompatible_with") or []
    if not isinstance(incompatible, list):
        incompatible = []

    features = data.get("features") or {}
    if not isinstance(features, dict):
        features = {}

    return ProductManifest(
        product_name=name,
        product_slug=slug,
        product_version=product_version,
        keprix_min_version=min_version,
        keprix_tested_against=tested_against,
        keprix_incompatible_with=[str(v) for v in incompatible],
        features=features,
        raw=data,
        path=path,
    )


def find_product_root(start: Path | None = None) -> Path:
    """Return the directory containing keprix.yaml, searching upward from start."""
    current = (start or Path.cwd()).expanduser().resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "keprix.yaml").exists():
            return candidate
    raise FileNotFoundError(
        "No keprix.yaml found. Run from a product directory or pass --path."
    )


def update_tested_against(manifest_path: Path, new_version: str) -> None:
    """Update tested_against in keprix.yaml after a successful upgrade."""
    manifest = load_product_manifest(manifest_path)
    data = dict(manifest.raw)
    data.setdefault("keprix", {})
    if not isinstance(data["keprix"], dict):
        data["keprix"] = {}
    data["keprix"]["tested_against"] = new_version
    manifest_path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
