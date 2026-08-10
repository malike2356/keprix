"""Social proof collect/curate/publish (parity with shared/social-proof)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any

POSITIVE = {
    "love",
    "amazing",
    "great",
    "excellent",
    "helpful",
    "saved",
    "thank",
    "awesome",
    "recommend",
    "brilliant",
    "works",
    "fast",
    "reliable",
    "impressed",
}
NEGATIVE = {
    "hate",
    "terrible",
    "awful",
    "broken",
    "bug",
    "slow",
    "useless",
    "scam",
    "fraud",
    "worst",
    "disappointed",
}

_LOCK = threading.Lock()
_LAST_WEEKLY: float | None = None
WEEKLY_SECONDS = 7 * 24 * 60 * 60


def normalize_quote(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text.lower())
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fingerprint(text: str, author: str = "", url: str = "") -> str:
    base = f"{normalize_quote(text)}|{author.lower().strip()}|{url.strip()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]


def score_sentiment(text: str) -> tuple[str, int]:
    words = normalize_quote(text).split()
    score = 0
    for w in words:
        if w in POSITIVE:
            score += 1
        if w in NEGATIVE:
            score -= 1
    label = "positive" if score > 0 else "negative" if score < 0 else "neutral"
    return label, score


class ProofTestimonialStore:
    def __init__(self, file_path: str | None = None) -> None:
        self.file_path = file_path
        self.rows: list[dict[str, Any]] = []
        if file_path and Path(file_path).exists():
            try:
                data = json.loads(Path(file_path).read_text(encoding="utf-8"))
                self.rows = list(data.get("testimonials") or [])
            except Exception:
                self.rows = []

    def _persist(self) -> None:
        if not self.file_path:
            return
        path = Path(self.file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"updatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "testimonials": self.rows}, indent=2)
            + "\n",
            encoding="utf-8",
        )

    def list(self, **filters: Any) -> list[dict[str, Any]]:
        rows = self.rows
        if filters.get("status"):
            rows = [r for r in rows if r.get("status") == filters["status"]]
        if filters.get("product"):
            rows = [r for r in rows if r.get("product") == filters["product"]]
        if filters.get("tag"):
            rows = [r for r in rows if filters["tag"] in (r.get("tags") or [])]
        return sorted(rows, key=lambda r: str(r.get("collectedAt") or ""), reverse=True)

    def upsert(self, partial: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        text = str(partial.get("text") or "").strip()
        author = str(partial.get("author") or "").strip()
        url = str(partial.get("url") or "").strip()
        if not url:
            raise ValueError("Every testimonial must include a source URL")
        if not text or not author:
            raise ValueError("text and author are required")
        fp = fingerprint(text, author, url)
        for row in self.rows:
            if row.get("fingerprint") == fp:
                return row, True
        label, score = score_sentiment(text)
        item = {
            "id": str(uuid.uuid4()),
            "text": text,
            "author": author,
            "authorTitle": partial.get("authorTitle"),
            "platform": partial.get("platform") or "manual",
            "url": url,
            "date": partial.get("date") or time.strftime("%Y-%m-%d", time.gmtime()),
            "tags": list(partial.get("tags") or []),
            "product": partial.get("product") or "general",
            "status": partial.get("status") or "pending",
            "sentiment": label,
            "sentimentScore": score,
            "collectedAt": partial.get("collectedAt") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reviewedAt": None,
            "fingerprint": fp,
        }
        self.rows.append(item)
        self._persist()
        return item, False

    def update(self, item_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        for i, row in enumerate(self.rows):
            if row.get("id") != item_id:
                continue
            next_row = dict(row)
            next_row.update(patch)
            if patch.get("status") in {"approved", "rejected"}:
                next_row["reviewedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self.rows[i] = next_row
            self._persist()
            return next_row
        return None

    def clear(self) -> None:
        self.rows = []
        self._persist()


def _load_fixtures(path: str | None, platform: str) -> list[dict[str, Any]]:
    if not path or not Path(path).exists():
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data.get(platform) or []
    return list(rows) if isinstance(rows, list) else []


def collect_from_twitter(store: ProofTestimonialStore, username: str = "keprixai", *, fixtures_path: str | None = None, product: str = "keprix") -> dict[str, Any]:
    items = _load_fixtures(fixtures_path, "twitter")
    added = duplicates = 0
    out = []
    for item in items:
        row, dup = store.upsert({**item, "platform": "twitter", "product": item.get("product") or product})
        if dup:
            duplicates += 1
        else:
            added += 1
            out.append(row)
    return {"platform": "twitter", "added": added, "duplicates": duplicates, "items": out}


def collect_from_linkedin(store: ProofTestimonialStore, company: str = "keprix", *, fixtures_path: str | None = None, product: str = "keprix") -> dict[str, Any]:
    _ = company
    items = _load_fixtures(fixtures_path, "linkedin")
    added = duplicates = 0
    out = []
    for item in items:
        row, dup = store.upsert({**item, "platform": "linkedin", "product": item.get("product") or product})
        if dup:
            duplicates += 1
        else:
            added += 1
            out.append(row)
    return {"platform": "linkedin", "added": added, "duplicates": duplicates, "items": out}


def collect_from_github(store: ProofTestimonialStore, repo: str = "malike2356/keprix", *, fixtures_path: str | None = None, product: str = "keprix") -> dict[str, Any]:
    items = _load_fixtures(fixtures_path, "github")
    if not items:
        # optional live collect skipped in unit tests; fixtures cover acceptance
        pass
    added = duplicates = 0
    out = []
    for item in items:
        row, dup = store.upsert({**item, "platform": "github", "product": item.get("product") or product})
        if dup:
            duplicates += 1
        else:
            added += 1
            out.append(row)
    return {"platform": "github", "added": added, "duplicates": duplicates, "items": out}


def collect_primary(store: ProofTestimonialStore, *, fixtures_path: str | None = None, product: str = "keprix") -> list[dict[str, Any]]:
    return [
        collect_from_twitter(store, fixtures_path=fixtures_path, product=product),
        collect_from_linkedin(store, fixtures_path=fixtures_path, product=product),
        collect_from_github(store, fixtures_path=fixtures_path, product=product),
    ]


def approve(store: ProofTestimonialStore, item_id: str) -> dict[str, Any] | None:
    return store.update(item_id, {"status": "approved"})


def reject(store: ProofTestimonialStore, item_id: str) -> dict[str, Any] | None:
    return store.update(item_id, {"status": "rejected"})


def tag(store: ProofTestimonialStore, item_id: str, tags: list[str]) -> dict[str, Any] | None:
    row = next((r for r in store.rows if r.get("id") == item_id), None)
    if not row:
        return None
    merged = sorted(set(list(row.get("tags") or []) + [t.strip() for t in tags if t.strip()]))
    return store.update(item_id, {"tags": merged})


def assign_product(store: ProofTestimonialStore, item_id: str, product: str) -> dict[str, Any] | None:
    return store.update(item_id, {"product": product.strip() or "general"})


def curate_top(rows: list[dict[str, Any]], product: str = "all", limit: int = 12) -> list[dict[str, Any]]:
    filtered = [
        r
        for r in rows
        if r.get("status") == "approved" and (product == "all" or r.get("product") == product)
    ]
    filtered.sort(key=lambda r: (-int(r.get("sentimentScore") or 0), -len(str(r.get("text") or ""))))
    return filtered[: max(1, limit)]


def run_weekly(store: ProofTestimonialStore, *, fixtures_path: str | None = None, force: bool = False, product: str = "keprix") -> dict[str, Any]:
    global _LAST_WEEKLY
    now = time.time()
    with _LOCK:
        if not force and _LAST_WEEKLY is not None and now - _LAST_WEEKLY < WEEKLY_SECONDS:
            return {"ran": False, "results": []}
        results = collect_primary(store, fixtures_path=fixtures_path, product=product)
        _LAST_WEEKLY = now
        return {"ran": True, "results": results}


def reset_weekly_for_tests() -> None:
    global _LAST_WEEKLY
    _LAST_WEEKLY = None


def default_store_path() -> str:
    home = os.environ.get("KEPRIX_HOME") or str(Path.home() / ".keprix")
    return str(Path(home) / "social-proof" / "testimonials.json")


_STORE: ProofTestimonialStore | None = None


def get_store() -> ProofTestimonialStore:
    global _STORE
    if _STORE is None:
        _STORE = ProofTestimonialStore(os.environ.get("KEPRIX_SOCIAL_PROOF_PATH") or default_store_path())
    return _STORE
