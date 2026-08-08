"""Product sidecar foundation for Carina/Aiva (and future product packs).

Northbound contract: ``/v1/products/{product_key}``.
Shell stays Carina/Aiva; Keprix is the brain via advertised capability nodes only.
"""

from __future__ import annotations

from keprix.product_sidecar.registry import get_product_pack_registry

__all__ = ["get_product_pack_registry"]
