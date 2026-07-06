"""Config-driven registry for products built on Keprix."""

from keprix.products.loader import (
    get_default_audit_domain_pack,
    get_product,
    get_product_feature_flags,
    get_regulated_domains,
    list_enabled_products,
    load_products_config,
    products_config_path,
    reset_products_cache,
    resolve_config_path,
    resolve_repo_root,
)
from keprix.products.models import ProductDefinition

__all__ = [
    "ProductDefinition",
    "get_default_audit_domain_pack",
    "get_product",
    "get_product_feature_flags",
    "get_regulated_domains",
    "list_enabled_products",
    "load_products_config",
    "products_config_path",
    "reset_products_cache",
    "resolve_config_path",
    "resolve_repo_root",
]
