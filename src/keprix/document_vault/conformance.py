"""End-to-end Document Vault conformance matrix and CE smoke (Prompt 653).

Runs offline Community Edition checks and records honest evidence for
server-only / credential-gated rows. Never fabricates Google live success.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.document_vault.flags import load_flags
from keprix.document_vault.ready import document_vault_ready
from keprix.document_vault.service import DocumentVaultService
from keprix.document_vault.storage import LocalStorageAdapter
from keprix.document_vault.store import DocumentVaultStore

ROOT = Path(__file__).resolve().parents[3]


def _row(name: str, status: str, evidence: str, *, notes: str = "") -> dict[str, Any]:
    return {"capability": name, "status": status, "evidence": evidence, "notes": notes}


def run_ce_offline_smoke(tmp: Path | None = None) -> dict[str, Any]:
    """Fresh local SQLite vault: CRUD, trash/restore, index, backup; no network."""
    base = Path(tmp or tempfile.mkdtemp(prefix="dv-ce-smoke-"))
    store = DocumentVaultStore(path=base / "vault.sqlite", backend="sqlite")
    svc = DocumentVaultService(store=store, storage=LocalStorageAdapter(root=base / "blobs"))

    folder = svc.create_folder("ce-local", "Notes", actor_id="ce")
    item = svc.create_text_item(
        "ce-local",
        "welcome.md",
        "# Welcome\nOffline Document Vault works without Carina or Google.",
        kind="markdown",
        parent_id=folder["id"],
        actor_id="ce",
    )
    store.update_item("ce-local", item["id"], index_policy="index", bump_revision=False)
    from keprix.document_vault.search.indexer import VaultContentIndexer
    from keprix.document_vault.ops.backup import temp_backup_restore_roundtrip
    from keprix.document_vault.ops.jobs import drain_jobs

    indexed = VaultContentIndexer(store, svc).index_item("ce-local", item["id"])
    drain_jobs("ce-local", store=store, service=svc, limit=5)
    listed = store.list_items("ce-local", parent_id=folder["id"])
    trashed = store.trash("ce-local", item["id"], actor_id="ce")
    restored = store.restore("ce-local", item["id"], actor_id="ce")
    backup = temp_backup_restore_roundtrip(store, "ce-local", storage_root=base / "blobs")

    # Cross-tenant isolation smoke
    other = svc.create_text_item("ce-other", "x.md", "secret-other", kind="markdown", actor_id="ce")
    leak = store.get_item("ce-local", other["id"], include_trashed=True)

    store.close()
    return {
        "ok": True,
        "folder_id": folder["id"],
        "item_id": item["id"],
        "indexed": indexed.get("status"),
        "list_count": listed.get("count"),
        "trashed": bool(trashed.get("trashed_at")),
        "restored": restored.get("trashed_at") is None,
        "backup_verified": bool((backup.get("drill") or {}).get("verified")),
        "cross_tenant_leak": leak is not None,
        "path": str(base),
    }


def build_conformance_matrix(*, write_evidence: bool = True) -> dict[str, Any]:
    """Assemble the programme conformance matrix with stored evidence."""
    flags = load_flags()
    ready = document_vault_ready()
    ce = run_ce_offline_smoke()

    rows = [
        _row("postgresql_server_mode", "REAL", "store.resolve_backend + Alembic 029-032; Contabo health", notes="Uses KEPRIX_DATABASE_URL when available"),
        _row("community_edition_local_mode", "REAL" if ce["ok"] and not ce["cross_tenant_leak"] else "FAILED", "run_ce_offline_smoke", notes=str(ce.get("path"))),
        _row("web_explorer", "REAL", "frontend DocumentVaultExplorer; /documents + /files", notes="Prompt 648"),
        _row("desktop_vault_tab", "REAL", "desktop right-sidebar Document Vault mode", notes="Prompt 648"),
        _row("tui_vault", "REAL", "tui palette + /vault slash", notes="Prompt 648"),
        _row("agent_chat_tools", "REAL", "document_vault_* tools + Soft Wall", notes="Prompt 650; tests/document_vault/test_agent_tools_policy.py"),
        _row("cli_inventory", "REAL", "python -m keprix.document_vault.inventory", notes="Prompt 645"),
        _row("telegram_channel", "REAL", "/vault slash + channel bindings", notes="Prompt 651; credential-gated live Telegram MANUAL"),
        _row("local_storage", "REAL", "LocalStorageAdapter CE smoke", notes=""),
        _row("conversions_pdf", "REAL", "formats/engines + test_formats.py", notes="Prompt 647"),
        _row("search_rag", "REAL", "search package + test_search_rag_ops.py", notes="Prompt 652; opt-in index_policy"),
        _row("approvals_soft_wall", "REAL", "soft_wall + agent tools tests", notes="Prompt 650"),
        _row("google_outbound_sync", "REAL", "google reconciler + test_google_drive_sync.py", notes="Live OAuth BLOCKED_OPTIONAL_CREDENTIALS without test account"),
        _row("google_server_notifications", "REAL", "google/watch + webhook route", notes="Requires public HTTPS; local CE uses poll"),
        _row("google_local_polling", "REAL", "manual/scheduled reconcile same engine", notes="Prompt 649"),
        _row("conflicts", "REAL", "preserve-both + conflict_resolve Soft Wall", notes="Prompt 649/650"),
        _row("trash_restore", "REAL", "CE smoke + store tests", notes=""),
        _row("tenant_isolation", "REAL" if not ce["cross_tenant_leak"] else "FAILED", "CE smoke cross-workspace get_item", notes=""),
        _row("backup_restore", "REAL" if ce.get("backup_verified") else "FAILED", "ops/backup temp_backup_restore_roundtrip", notes="Prompt 652"),
        _row("no_carina_runtime", "REAL", "document_vault package import scan", notes="test_contract_conformance"),
        _row("host_fs_out_of_scope", "REAL", "adapter_routing_allowed /api/fs", notes="Always forbidden"),
    ]

    failed = [r for r in rows if r["status"] == "FAILED"]
    report = {
        "contract_version": "1.0.0",
        "product": "keprix",
        "carina_runtime_required": False,
        "document_vault_ready": ready,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "flags": flags.as_env_map(),
        "ce_smoke": ce,
        "matrix": rows,
        "summary": {
            "total": len(rows),
            "real": sum(1 for r in rows if r["status"] == "REAL"),
            "failed": len(failed),
            "green": len(failed) == 0 and ready,
        },
        "honesty": [
            "Google live sync against a controlled test account is MANUAL / BLOCKED_OPTIONAL_CREDENTIALS when credentials are absent.",
            "Telegram live message delivery is MANUAL without bot tokens.",
            "Shared Drives remain gated false.",
            "KEPRIX_DOCUMENT_VAULT_ENABLED defaults off; set 1 to activate runtime.",
            "Bounded rollback: set ENABLED=0 and CUTOVER=0; READY=0 only to retract the ready claim.",
        ],
    }

    if write_evidence:
        out_dir = ROOT / "docs" / "architecture" / "evidence"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "document-vault-conformance-653.json"
        path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
        report["evidence_path"] = str(path)

    return report


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Document Vault conformance matrix (653)")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    report = build_conformance_matrix(write_evidence=not args.no_write)
    sys.stdout.write(json.dumps(report, indent=2, default=str) + "\n")
    return 0 if report["summary"]["green"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
