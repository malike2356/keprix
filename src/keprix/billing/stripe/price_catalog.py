"""Load operator Stripe price labels from a local credentials/catalog markdown file.

Keprix is open source. Do not ship live Stripe price IDs in code. Operators pin
their own `price_*` values via `KEPRIX_STRIPE_CREDENTIALS_FILE` and `billing.yaml`.

When the catalog markdown uses section headers (``#Scout``, ``#Keprix``, …), the
admin dropdown defaults to Keprix-relevant sections only so Scout/Carina/Aiva
prices do not appear in a Keprix UI.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from keprix.billing.stripe.credentials import _candidate_paths


@dataclass(frozen=True)
class StripePriceCatalogEntry:
    label: str
    price_id: str
    amount: int | None = None
    currency: str = "gbp"
    interval: str | None = None
    section: str = ""


_PRICE_LINE = re.compile(r"^\s*(?:[-*]\s*)?(.+?)\s*(?::|=)\s*`?(price_[A-Za-z0-9_]+)`?")
_GBP_AMOUNT = re.compile(r"£\s*([0-9]+(?:\.[0-9]{1,2})?)")
_SECTION_HEADER = re.compile(r"^\s*#\s*(.+?)\s*$")
_PRODUCT_SECTION = re.compile(
    r"^(keprix|scout|carina|aiva|propreneur|verlox|generic)\b",
    re.IGNORECASE,
)

# Substrings matched against markdown section headers (case-insensitive).
_DEFAULT_KEPRIX_SECTION_KEYWORDS = (
    "keprix",
    "verlox saas",
    "generic verlox",
    "verlox test",
)


def _amount_from_label(label: str) -> int | None:
    match = _GBP_AMOUNT.search(label)
    if not match:
        return None
    return int(round(float(match.group(1)) * 100))


def _interval_from_label(label: str) -> str | None:
    lower = label.lower()
    if any(token in lower for token in ("/yr", "/year", " yearly", " annual")):
        return "year"
    if any(token in lower for token in ("/mo", "/month", " monthly")):
        return "month"
    if any(
        token in lower
        for token in (
            "one-off",
            "one off",
            "one-time",
            "one time",
            "donation",
            "prepaid",
            "top up",
            "top-up",
        )
    ):
        return None
    return "month" if "£" in label else None


def _keprix_section_keywords() -> tuple[str, ...]:
    raw = os.environ.get("KEPRIX_STRIPE_CATALOG_SECTIONS", "").strip()
    if not raw:
        return _DEFAULT_KEPRIX_SECTION_KEYWORDS
    parts = [part.strip().lower() for part in raw.split(",") if part.strip()]
    return tuple(parts) or _DEFAULT_KEPRIX_SECTION_KEYWORDS


def _section_allowed(section: str, *, scope: str) -> bool:
    if scope == "all":
        return True
    # Flat catalogs (no headers), common in tests / single-product deploy files.
    if not section.strip():
        return True
    lower = section.lower()
    return any(keyword in lower for keyword in _keprix_section_keywords())


def load_price_catalog(*, scope: str | None = None) -> list[StripePriceCatalogEntry]:
    """Parse price lines from the operator credentials/catalog file.

    ``scope``:
    - ``keprix`` (default): only Keprix-relevant markdown sections
    - ``all``: every price line in the file (escape hatch for operators)
    """
    resolved_scope = (scope or os.environ.get("KEPRIX_STRIPE_CATALOG_SCOPE", "keprix")).strip().lower()
    if resolved_scope not in {"keprix", "all"}:
        resolved_scope = "keprix"

    entries: list[StripePriceCatalogEntry] = []
    seen: set[tuple[str, str]] = set()
    for path in _candidate_paths():
        if not path.is_file():
            continue
        section = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            header = _SECTION_HEADER.match(line)
            if header:
                title = header.group(1).strip()
                # Only real product section titles change scope (not # NOTE / prose).
                if not _PRODUCT_SECTION.match(title):
                    continue
                section = title
                continue
            match = _PRICE_LINE.match(line)
            if not match:
                continue
            if not _section_allowed(section, scope=resolved_scope):
                continue
            label = match.group(1).strip().strip("`").strip()
            price_id = match.group(2).strip()
            key = (label.lower(), price_id)
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                StripePriceCatalogEntry(
                    label=label,
                    price_id=price_id,
                    amount=_amount_from_label(label),
                    interval=_interval_from_label(label),
                    section=section,
                )
            )
    return entries


def find_price_by_label(label: str) -> StripePriceCatalogEntry | None:
    wanted = label.strip().lower()
    for entry in load_price_catalog(scope="all"):
        if entry.label.strip().lower() == wanted:
            return entry
    return None


def find_price_by_amount(
    *,
    amount: int,
    currency: str = "gbp",
    interval: str | None = "month",
) -> StripePriceCatalogEntry | None:
    matches = [
        entry
        for entry in load_price_catalog(scope="keprix")
        if entry.amount == amount and entry.currency == currency and entry.interval == interval
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def find_price_by_id(price_id: str, *, scope: str = "all") -> StripePriceCatalogEntry | None:
    wanted = price_id.strip()
    if not wanted:
        return None
    for entry in load_price_catalog(scope=scope):
        if entry.price_id == wanted:
            return entry
    return None


def coffee_donation_price_id() -> str | None:
    """Optional legacy catalog pin from billing.yaml donations; open amounts use price_data."""
    try:
        from keprix.billing.config_loader import load_billing_config

        cfg = load_billing_config()
        if cfg is None:
            return None
        for donation in cfg.donations:
            if donation.id == "coffee" and donation.stripe_price_id:
                return donation.stripe_price_id
        for donation in cfg.donations:
            if donation.stripe_price_id:
                return donation.stripe_price_id
    except Exception:
        return None
    return None
