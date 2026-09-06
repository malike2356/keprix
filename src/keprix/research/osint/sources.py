"""Allowlisted adapters for the public OSINT fetch scripts."""

from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from .entity import Entity

SCRIPT_DIR = Path(__file__).parents[2] / "optional-skills" / "research" / "osint-investigation" / "scripts"

DEFAULT_SOURCES: dict[str, tuple[str, ...]] = {
    "company": ("opencorporates", "wikipedia", "sec_edgar"),
    "person": ("wikipedia", "courtlistener"),
    "domain": ("wayback", "gdelt"),
}


def _load_fetcher(name: str) -> Callable[..., int]:
    if not name.replace("_", "").isalnum() or name.startswith("_"):
        raise ValueError("invalid OSINT source name")
    path = SCRIPT_DIR / f"fetch_{name}.py"
    if not path.is_file():
        raise ValueError(f"unknown OSINT source: {name}")
    spec = importlib.util.spec_from_file_location(f"keprix_osint_{name}", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load OSINT source: {name}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(SCRIPT_DIR))
    fetch = getattr(module, "fetch", None)
    if not callable(fetch):
        raise ValueError(f"OSINT source has no fetch function: {name}")
    return fetch


def _query(entity: Entity) -> str:
    return entity.name or next(iter(entity.identifiers), "")


def _invoke(name: str, entity: Entity, out_path: str, limit: int) -> int:
    fetch = _load_fetcher(name)
    query = _query(entity)
    seed = {str(key): str(value) for key, value in entity.seed.items() if value}
    if name == "opencorporates":
        return fetch(query, seed.get("jurisdiction"), None, limit, out_path)
    if name == "wikipedia":
        return fetch(query, limit, False, out_path)
    if name == "wayback":
        return fetch(seed.get("domain") or query, "domain", None, None, "200", None, "urlkey", limit, out_path)
    if name == "gdelt":
        return fetch(query, "artlist", None, None, None, None, None, limit, out_path)
    if name == "sec_edgar":
        return fetch(seed.get("cik"), query, [], None, out_path)
    if name == "courtlistener":
        return fetch(query, "o", None, None, None, None, limit, out_path)
    raise ValueError(f"source is not configured: {name}")


def _evidence(name: str, row: dict[str, str]) -> dict[str, Any]:
    url = next((row.get(key, "").strip() for key in (
        "url", "source_url", "opencorporates_url", "wikipedia_url", "wikidata_url",
        "wayback_url", "filing_url", "absolute_url",
    ) if row.get(key)), "")
    claim = next((row.get(key, "").strip() for key in (
        "summary", "description", "title", "name", "company_name", "case_name", "label",
    ) if row.get(key)), "")
    result: dict[str, Any] = {"source": name, "url": url, "claim": claim}
    for key in ("company_number", "cik", "qid", "domain", "wikipedia_title"):
        if row.get(key):
            result[key] = row[key].strip()
    return result


def make_source(name: str, *, limit: int = 10) -> Callable[[Entity], list[dict[str, Any]]]:
    """Build one allowlisted adapter. Network failures become source errors."""

    if name not in {item for values in DEFAULT_SOURCES.values() for item in values}:
        raise ValueError(f"source is not allowlisted: {name}")
    bounded_limit = max(1, min(int(limit), 50))

    def fetch(entity: Entity) -> list[dict[str, Any]]:
        with tempfile.TemporaryDirectory(prefix="keprix-osint-") as directory:
            output = str(Path(directory) / "results.csv")
            try:
                _invoke(name, entity, output, bounded_limit)
                with open(output, newline="", encoding="utf-8") as handle:
                    return [_evidence(name, row) for row in csv.DictReader(handle)]
            except Exception as exc:  # noqa: BLE001
                return [{"source": name, "error": f"{type(exc).__name__}: {exc}"}]

    return fetch


def sources_for(kind: str, names: list[str] | None = None, *, limit: int = 10) -> dict[str, Callable[[Entity], list[dict[str, Any]]]]:
    selected = names if names is not None else list(DEFAULT_SOURCES.get(kind, ()))
    return {name: make_source(name, limit=limit) for name in selected}
