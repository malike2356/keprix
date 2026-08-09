"""Canonical SEO lead-tracker headers, aliases, and row normalization."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

# 17 reference headers (SEO lead tracker compatibility shape).
REFERENCE_HEADERS: tuple[str, ...] = (
    "Company",
    "Niche",
    "Town/City",
    "Website",
    "Contact Name",
    "Email",
    "Phone",
    "Google Reviews",
    "Google Rating",
    "Google Maps URL",
    "Website Score",
    "Ranks Top3?",
    "Weakness",
    "Priority",
    "Status",
    "Date Added",
    "Notes",
)

# Canonical internal field keys (order mirrors REFERENCE_HEADERS).
CANONICAL_KEYS: tuple[str, ...] = (
    "company_name",
    "niche",
    "locality",
    "website",
    "name",
    "email",
    "phone",
    "google_reviews",
    "google_rating",
    "google_maps_url",
    "website_score",
    "ranks_top3",
    "weakness",
    "priority",
    "stage",
    "source_captured_at",
    "notes",
)

REFERENCE_TO_CANONICAL: dict[str, str] = dict(zip(REFERENCE_HEADERS, CANONICAL_KEYS))

# Alias (normalized) -> canonical key.
ALIASES: dict[str, str] = {
    # company
    "company": "company_name",
    "company_name": "company_name",
    "organisation": "company_name",
    "organization": "company_name",
    "business": "company_name",
    "business_name": "company_name",
    # niche
    "niche": "niche",
    "category": "niche",
    "sector": "niche",
    "industry": "niche",
    # locality
    "town_city": "locality",
    "town": "locality",
    "city": "locality",
    "locality": "locality",
    "location": "locality",
    "region": "locality",
    # website
    "website": "website",
    "url": "website",
    "domain": "website",
    "homepage": "website",
    "web": "website",
    # contact name
    "contact_name": "name",
    "contact": "name",
    "full_name": "name",
    "name": "name",
    "person": "name",
    # email
    "email": "email",
    "e_mail": "email",
    "email_address": "email",
    "contact_email": "email",
    "work_email": "email",
    # phone
    "phone": "phone",
    "telephone": "phone",
    "mobile": "phone",
    "cell": "phone",
    "contact_phone": "phone",
    "phone_number": "phone",
    # google reviews / rating / maps
    "google_reviews": "google_reviews",
    "reviews": "google_reviews",
    "review_count": "google_reviews",
    "google_rating": "google_rating",
    "rating": "google_rating",
    "stars": "google_rating",
    "google_maps_url": "google_maps_url",
    "maps_url": "google_maps_url",
    "google_maps": "google_maps_url",
    "gmaps": "google_maps_url",
    # website score
    "website_score": "website_score",
    "site_score": "website_score",
    "seo_score": "website_score",
    # ranks top3
    "ranks_top3": "ranks_top3",
    "ranks_top_3": "ranks_top3",
    "top3": "ranks_top3",
    "ranks_top3_": "ranks_top3",
    # weakness / priority / status / notes
    "weakness": "weakness",
    "weaknesses": "weakness",
    "priority": "priority",
    "status": "stage",
    "stage": "stage",
    "pipeline_stage": "pipeline_stage",
    "date_added": "source_captured_at",
    "added": "source_captured_at",
    "captured_at": "source_captured_at",
    "source_captured_at": "source_captured_at",
    "notes": "notes",
    "note": "notes",
    "comments": "notes",
}


def normalize_header(value: str) -> str:
    text = (value or "").strip().lower()
    text = text.replace("/", " ")
    text = text.replace("?", "")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def map_headers(headers: list[str]) -> dict[str, str]:
    """Map original header labels -> canonical field keys.

    Unknown headers are omitted here; callers put them into custom_fields.
    """
    mapping: dict[str, str] = {}
    used_canonical: set[str] = set()
    for header in headers:
        norm = normalize_header(header)
        # Exact reference header match first.
        if header in REFERENCE_TO_CANONICAL:
            canonical = REFERENCE_TO_CANONICAL[header]
        else:
            canonical = ALIASES.get(norm)
            if canonical is None and norm.endswith("_"):
                canonical = ALIASES.get(norm.rstrip("_"))
        if not canonical:
            continue
        if canonical in used_canonical:
            continue
        mapping[header] = canonical
        used_canonical.add(canonical)
    return mapping


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def normalize_email(value: Any) -> str | None:
    if _is_blank(value):
        return None
    text = str(value).strip().lower()
    if "@" not in text:
        return text or None
    return text


def normalize_phone(value: Any) -> str | None:
    if _is_blank(value):
        return None
    text = str(value).strip()
    # Keep leading + and digits; drop common separators.
    kept = []
    for i, ch in enumerate(text):
        if ch.isdigit():
            kept.append(ch)
        elif ch == "+" and i == 0:
            kept.append(ch)
        elif ch in " ()-.":
            continue
        else:
            kept.append(ch)
    out = "".join(kept).strip()
    return out or None


def normalize_website(value: Any) -> str | None:
    if _is_blank(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    if "://" not in text:
        text = "https://" + text
    try:
        parsed = urlparse(text)
        host = (parsed.netloc or parsed.path).lower().rstrip("/")
        if host.startswith("www."):
            host = host[4:]
        path = parsed.path if parsed.netloc else ""
        if path in ("", "/"):
            return host or None
        return f"{host}{path}".rstrip("/") or None
    except Exception:
        return str(value).strip().lower() or None


def normalize_location(value: Any) -> str | None:
    if _is_blank(value):
        return None
    return re.sub(r"\s+", " ", str(value).strip())


def normalize_bool(value: Any) -> str | None:
    if _is_blank(value):
        return None
    if isinstance(value, bool):
        return "yes" if value else "no"
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "t", "rank", "ranked", "top3", "top 3"}:
        return "yes"
    if text in {"0", "false", "no", "n", "f"}:
        return "no"
    return str(value).strip()


def normalize_date(value: Any) -> str | None:
    if _is_blank(value):
        return None
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    text = str(value).strip()
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(text.replace("Z", "+0000"), fmt).date().isoformat()
        except ValueError:
            continue
    # ISO-ish passthrough
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return text


def normalize_rating(value: Any) -> str | None:
    if _is_blank(value):
        return None
    try:
        num = float(str(value).strip().replace(",", "."))
        return f"{num:.1f}".rstrip("0").rstrip(".") if num != int(num) else str(int(num))
    except ValueError:
        return str(value).strip()


def normalize_score(value: Any) -> str | None:
    if _is_blank(value):
        return None
    try:
        num = float(str(value).strip().replace(",", "."))
        if num == int(num):
            return str(int(num))
        return f"{num:.2f}".rstrip("0").rstrip(".")
    except ValueError:
        return str(value).strip()


_FIELD_NORMALIZERS = {
    "email": normalize_email,
    "phone": normalize_phone,
    "website": normalize_website,
    "google_maps_url": normalize_website,
    "locality": normalize_location,
    "ranks_top3": normalize_bool,
    "source_captured_at": normalize_date,
    "google_rating": normalize_rating,
    "google_reviews": normalize_score,
    "website_score": normalize_score,
}


def normalize_row(
    raw: dict[str, Any],
    *,
    header_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Map a raw row dict onto canonical fields + custom_fields."""
    headers = list(raw.keys())
    mapping = header_map if header_map is not None else map_headers([str(h) for h in headers])
    mapped: dict[str, Any] = {}
    custom: dict[str, Any] = {}
    for header, value in raw.items():
        header_s = str(header)
        canonical = mapping.get(header_s)
        if canonical is None:
            # Already-canonical keys pass through.
            if header_s in CANONICAL_KEYS or header_s in ALIASES.values():
                canonical = header_s
            elif normalize_header(header_s) in ALIASES:
                canonical = ALIASES[normalize_header(header_s)]
            else:
                if not _is_blank(value):
                    custom[header_s] = value if not isinstance(value, str) else value.strip()
                continue
        if _is_blank(value):
            continue
        normalizer = _FIELD_NORMALIZERS.get(canonical)
        mapped[canonical] = normalizer(value) if normalizer else (
            value.strip() if isinstance(value, str) else value
        )
    if custom:
        existing_custom = mapped.get("custom_fields")
        if isinstance(existing_custom, dict):
            merged = dict(existing_custom)
            merged.update(custom)
            mapped["custom_fields"] = merged
        else:
            mapped["custom_fields"] = custom
    # Mirror stage -> pipeline_stage when present.
    if mapped.get("stage") and not mapped.get("pipeline_stage"):
        mapped["pipeline_stage"] = mapped["stage"]
    return mapped
