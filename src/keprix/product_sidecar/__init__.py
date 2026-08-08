"""Product sidecar foundation for multi-product Keprix packs.

Northbound contract: ``/v1/products/{product_key}``.
"""

from __future__ import annotations

from keprix.product_sidecar.registry import get_product_pack_registry

__all__ = ["get_product_pack_registry"]
