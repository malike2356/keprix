"""Load enabled products from config/products.yaml (no hardcoded project names in core)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from keprix.products.models import ProductDefinition

_LOADED = False
_PRODUCTS: dict[str, ProductDefinition] = {}
_REGULATED_DOMAINS: frozenset[str] = frozenset()
_DEFAULT_AUDIT_DOMAIN_PACK: str | None = None
_MERGED_FEATURE_FLAGS: dict[str, bool] = {}


def resolve_repo_root() -> Path:
    env = os.environ.get("KEPRIX_REPO_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "config").is_dir():
            return parent
    for parent in here.parents:
        if (parent / "config").is_dir():
            return parent
    return Path.cwd().resolve()


def products_config_path() -> Path:
    env = os.environ.get("KEPRIX_PRODUCTS_CONFIG", "").strip()
    if env:
        return Path(env).resolve()
    root = resolve_repo_root()
    primary = root / "config" / "products.yaml"
    if primary.exists():
        return primary
    return root / "config" / "products.example.yaml"


def _env_enabled(product: ProductDefinition) -> bool:
    if product.env_flag:
        raw = os.environ.get(product.env_flag, "").strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True
    return False


def _extension_enabled(product: ProductDefinition) -> bool:
    if not product.extension_name:
        return False
    raw = os.environ.get("KEPRIX_ACTIVE_EXTENSIONS", "").strip()
    names = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return product.extension_name.lower() in names


def _explicit_enabled(product_id: str, product: ProductDefinition, row: dict[str, Any]) -> bool:
    if bool(row.get("enabled")):
        return True
    raw = os.environ.get("KEPRIX_ENABLED_PRODUCTS", "").strip()
    names = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return product_id.lower() in names or _env_enabled(product) or _extension_enabled(product)


def resolve_config_path(relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute():
        return path
    return resolve_repo_root() / path


def load_products_config(*, force: bool = False) -> dict[str, ProductDefinition]:
    global _LOADED, _PRODUCTS, _REGULATED_DOMAINS, _DEFAULT_AUDIT_DOMAIN_PACK, _MERGED_FEATURE_FLAGS
    if _LOADED and not force:
        return _PRODUCTS

    path = products_config_path()
    _PRODUCTS = {}
    _REGULATED_DOMAINS = frozenset()
    _DEFAULT_AUDIT_DOMAIN_PACK = None
    _MERGED_FEATURE_FLAGS = {}

    if not path.exists():
        _LOADED = True
        return _PRODUCTS

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    defaults = raw.get("defaults") or {}
    if defaults.get("regulated_domains"):
        _REGULATED_DOMAINS = frozenset(str(item) for item in defaults["regulated_domains"])
    if defaults.get("audit_domain_pack"):
        _DEFAULT_AUDIT_DOMAIN_PACK = str(defaults["audit_domain_pack"])

    for product_id, row in (raw.get("products") or {}).items():
        if not isinstance(row, dict):
            continue
        product = ProductDefinition.from_dict(str(product_id), row)
        if not _explicit_enabled(str(product_id), product, row):
            continue
        _PRODUCTS[product.id] = product
        if product.regulated_domains:
            _REGULATED_DOMAINS = _REGULATED_DOMAINS | frozenset(product.regulated_domains)
        if product.audit_domain_pack and _DEFAULT_AUDIT_DOMAIN_PACK is None:
            _DEFAULT_AUDIT_DOMAIN_PACK = product.audit_domain_pack
        _MERGED_FEATURE_FLAGS.update(product.feature_flags)

    _LOADED = True
    return _PRODUCTS


def list_enabled_products() -> list[ProductDefinition]:
    return list(load_products_config().values())


def get_product(product_id: str) -> ProductDefinition | None:
    return load_products_config().get(product_id)


def get_regulated_domains() -> frozenset[str]:
    load_products_config()
    return _REGULATED_DOMAINS


def get_default_audit_domain_pack() -> str | None:
    load_products_config()
    return _DEFAULT_AUDIT_DOMAIN_PACK


def get_product_feature_flags() -> dict[str, bool]:
    load_products_config()
    return dict(_MERGED_FEATURE_FLAGS)


def reset_products_cache() -> None:
    global _LOADED
    _LOADED = False
    load_products_config(force=True)
