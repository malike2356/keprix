"""Read-only Document Vault inventory and audit (Prompt 645).

Never mutates user content. Migration writers are gated separately in 646+.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

from keprix.document_vault.flags import load_flags
from keprix.document_vault.surfaces import SURFACES

ROOT = Path(__file__).resolve().parents[3]  # keprix/


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _scan_workspace_repo_samples(workspace_id: str) -> dict[str, Any]:
    """Sample in-memory workspace repo if process has docs (best-effort)."""
    try:
        from keprix.workspace.repository import workspace_repo
    except Exception as exc:
        return {"available": False, "error": str(exc)}

    docs = getattr(workspace_repo, "documents", None) or {}
    rows: list[dict[str, Any]] = []
    if isinstance(docs, dict):
        for doc_id, doc in list(docs.items())[:500]:
            if not isinstance(doc, dict):
                continue
            owner = str(doc.get("user_id") or doc.get("workspace_id") or "")
            if workspace_id and owner and owner != workspace_id and workspace_id != "local":
                continue
            content = str(doc.get("content") or "")
            rows.append(
                {
                    "source": "workspace_repo",
                    "id": str(doc_id),
                    "title": doc.get("title"),
                    "checksum": _sha256_text(content),
                    "bytes": len(content.encode("utf-8")),
                }
            )
    return {"available": True, "count": len(rows), "samples": rows}


def _duplicate_report(samples: list[dict[str, Any]]) -> dict[str, Any]:
    by_id: dict[str, list[str]] = defaultdict(list)
    by_checksum: dict[str, list[str]] = defaultdict(list)
    for row in samples:
        rid = str(row.get("id") or "")
        chk = str(row.get("checksum") or "")
        src = str(row.get("source") or "")
        if rid:
            by_id[rid].append(src)
        if chk:
            by_checksum[chk].append(f"{src}:{rid}")
    id_dups = {k: v for k, v in by_id.items() if len(v) > 1}
    checksum_dups = {k: v for k, v in by_checksum.items() if len(set(v)) > 1}
    return {
        "duplicate_ids": id_dups,
        "duplicate_checksums": checksum_dups,
        "duplicate_id_count": len(id_dups),
        "duplicate_checksum_count": len(checksum_dups),
    }


def _orphan_and_conflict_stubs() -> dict[str, Any]:
    """Orphan placeholders; live scans available via ops.repair when enabled."""
    return {
        "orphans": {
            "versions_without_parent": [],
            "mappings_without_item": [],
            "index_entries_without_item": [],
        },
        "identifier_conflicts": [],
        "note": "Use POST /api/document-vault/ops/repair/orphans for live orphan repair (652).",
    }


def build_inventory_report(
    workspace_id: str = "local",
    *,
    dry_run: bool = True,
    root: Path | None = None,
) -> dict[str, Any]:
    """Produce a read-only inventory / audit report.

    ``dry_run`` must remain True for Prompt 645 callers. Setting False without
    migrate flag still refuses mutation.
    """
    root = root or ROOT
    flags = load_flags()
    mutated = False
    if not dry_run and not flags.migrate:
        # Refuse writers; still return report.
        dry_run = True

    present: list[dict[str, Any]] = []
    missing: list[str] = []
    for surface in SURFACES:
        path = root / surface.path
        exists = path.exists()
        entry = {
            **asdict(surface),
            "exists": exists,
        }
        present.append(entry)
        if not exists:
            missing.append(surface.key)

    repo = _scan_workspace_repo_samples(workspace_id)
    samples = list(repo.get("samples") or [])
    dupes = _duplicate_report(samples)
    orphans = _orphan_and_conflict_stubs()

    category_counts = Counter(s.category for s in SURFACES)

    report = {
        "contract_version": "1.0.0",
        "product": "keprix",
        "carina_runtime_required": False,
        "workspace_id": workspace_id,
        "dry_run": True if not flags.migrate else bool(dry_run),
        "mutated": mutated,
        "flags": flags.as_env_map(),
        "surfaces": {
            "total": len(SURFACES),
            "present": sum(1 for s in present if s["exists"]),
            "missing": missing,
            "by_category": dict(category_counts),
            "items": present,
        },
        "content_samples": repo,
        "duplicates": dupes,
        "orphans": orphans["orphans"],
        "identifier_conflicts": orphans["identifier_conflicts"],
        "notes": [
            orphans["note"],
            "Admin host FS and credential vault are never migrate targets.",
            "KEPRIX_DOCUMENT_VAULT_HOST_FS_BRIDGE is always false.",
            "Programme closed in Prompt 653; enable with KEPRIX_DOCUMENT_VAULT_ENABLED=1.",
        ],
        "document_vault_ready": flags.ready,
    }
    # Integrity: never claim mutation in 645 inventory path.
    assert report["mutated"] is False
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Keprix Document Vault read-only inventory")
    parser.add_argument("--workspace-id", default="local")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true", default=True)
    args = parser.parse_args(argv)
    report = build_inventory_report(args.workspace_id, dry_run=True)
    sys.stdout.write(json.dumps(report, indent=2, default=str) + "\n")
    return 0 if report.get("mutated") is False else 2


if __name__ == "__main__":
    raise SystemExit(main())
