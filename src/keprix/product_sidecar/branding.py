"""User-facing product copy for white-label product packs."""

from __future__ import annotations

import os


def display_product_name(product_key: str, *, internal: bool = False) -> str:
    if internal or product_key != "propreneur":
        return product_key.replace("_", " ").title()
    return os.environ.get("KEPRIX_PROPRENEUR_DISPLAY_NAME", "Property Manager")


def masked_copy(text: str, *, internal: bool = False) -> str:
    if internal:
        return text
    return text.replace("Propreneur", display_product_name("propreneur"))
