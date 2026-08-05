"""Individual readiness checks (market, upgrade, recovery)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from keprix.readiness.models import CheckResult
from keprix.readiness.restore_evidence import RestoreEvidenceStore, get_restore_evidence_store


def check_auth() -> CheckResult:
    try:
        from keprix.auth.config import auth_enabled

        enabled = auth_enabled()
        if enabled:
            return CheckResult(
                id="auth",
                title="Authentication",
                category="market",
                status="pass",
                summary="Auth is enabled for this deployment.",
                fix_path="/settings/security",
                docs_path="docs/features/settings.md",
            )
        return CheckResult(
            id="auth",
            title="Authentication",
            category="market",
            status="warn",
            summary="Auth is disabled (local/dev mode). Enable before public hosting.",
            fix_path="/settings/security",
            docs_path="docs/operations/admin-dashboard.md",
            evidence={"auth_enabled": False},
        )
    except Exception as exc:
        return CheckResult(
            id="auth",
            title="Authentication",
            category="market",
            status="unknown",
            summary=f"Could not evaluate auth: {exc}",
            fix_path="/settings/security",
        )


def check_billing_prices(*, load_config: Callable[[], Any] | None = None) -> CheckResult:
    """Fail when paid plans/addons lack Stripe price IDs. Donation gaps are warn-only."""
    try:
        from keprix.billing.config_loader import load_billing_config

        loader = load_config or load_billing_config
        cfg = loader()
        if cfg is None:
            return CheckResult(
                id="billing_prices",
                title="Billing Stripe price IDs",
                category="market",
                status="warn",
                summary="Billing config not loaded (self-hosted/community may skip hosted billing).",
                fix_path="/settings/billing",
                docs_path="docs/features/billing.md",
                evidence={"billing_config": False},
            )

        missing_required: list[str] = []
        missing_donation: list[str] = []
        for plan in cfg.plans:
            for price_cfg in plan.resolved_prices():
                if int(price_cfg.amount or 0) == 0:
                    continue
                if not price_cfg.stripe_price_id:
                    missing_required.append(f"plan:{plan.id}:{price_cfg.interval or 'once'}")
        for addon in cfg.addons:
            if int(addon.price or 0) == 0:
                continue
            if not addon.stripe_price_id:
                missing_required.append(f"addon:{addon.id}")
        for donation in cfg.donations:
            # Voluntary; never fail market readiness for missing donation price.
            if not donation.stripe_price_id:
                missing_donation.append(donation.id)

        if missing_required:
            return CheckResult(
                id="billing_prices",
                title="Billing Stripe price IDs",
                category="market",
                status="fail",
                summary="Paid plans/addons are missing Stripe price IDs from the canonical catalog.",
                fix_path="/settings/billing",
                docs_path="docs/features/billing.md",
                evidence={"missing_price_ids": missing_required, "missing_donations": missing_donation},
            )
        if missing_donation:
            return CheckResult(
                id="billing_prices",
                title="Billing Stripe price IDs",
                category="market",
                status="warn",
                summary="Optional donation price IDs are unset. Community coffee donation stays voluntary.",
                fix_path="/settings/billing",
                docs_path="docs/features/billing.md",
                evidence={"missing_donations": missing_donation, "donation_voluntary": True},
            )
        return CheckResult(
            id="billing_prices",
            title="Billing Stripe price IDs",
            category="market",
            status="pass",
            summary="Required Stripe price IDs are present. Donation remains voluntary.",
            fix_path="/settings/billing",
            docs_path="docs/features/billing.md",
            evidence={"donation_voluntary": True},
        )
    except Exception as exc:
        return CheckResult(
            id="billing_prices",
            title="Billing Stripe price IDs",
            category="market",
            status="unknown",
            summary=f"Could not evaluate billing prices: {exc}",
            fix_path="/settings/billing",
        )


def check_byok_and_wallet() -> CheckResult:
    try:
        from keprix.billing.config_loader import billing_enabled
        from keprix.billing.wallet.policy import is_hosted_deployment
        from keprix.licensing.edition import current_edition

        hosted = is_hosted_deployment()
        edition = current_edition()
        evidence = {"hosted": hosted, "edition": edition, "billing_enabled": billing_enabled()}
        if hosted and billing_enabled():
            return CheckResult(
                id="wallet_byok",
                title="BYOK and managed wallet",
                category="market",
                status="pass",
                summary="Hosted billing is enabled; managed wallet and BYOK paths are available.",
                fix_path="/settings/billing",
                docs_path="docs/features/billing.md",
                evidence=evidence,
            )
        return CheckResult(
            id="wallet_byok",
            title="BYOK and managed wallet",
            category="market",
            status="pass",
            summary="Self-hosted/community defaults to BYOK. Managed wallet is optional.",
            fix_path="/settings/keys",
            docs_path="docs/features/billing.md",
            evidence=evidence,
        )
    except Exception as exc:
        return CheckResult(
            id="wallet_byok",
            title="BYOK and managed wallet",
            category="market",
            status="unknown",
            summary=f"Could not evaluate wallet policy: {exc}",
            fix_path="/settings/billing",
        )


def check_quotas() -> CheckResult:
    try:
        from keprix.quotas.policy import deployment_tier
        from keprix.quotas.actor_store import get_actor_quota_store

        tier = deployment_tier()
        store = get_actor_quota_store()
        # Presence of store is enough; limits resolve per tier.
        _ = store
        return CheckResult(
            id="quotas",
            title="Actor and product quotas",
            category="market",
            status="pass",
            summary=f"Quota subsystem available (tier={tier}).",
            fix_path="/admin/quotas",
            docs_path="docs/features/quotas.md",
            evidence={"tier": tier},
        )
    except Exception as exc:
        return CheckResult(
            id="quotas",
            title="Actor and product quotas",
            category="market",
            status="fail",
            summary=f"Quota subsystem unavailable: {exc}",
            fix_path="/admin/quotas",
            docs_path="docs/features/quotas.md",
        )


def check_tool_acls() -> CheckResult:
    try:
        from keprix.security.tool_acl import get_tool_acl
        from keprix.security.resource_scopes.grants import get_resource_grant_store

        acl = get_tool_acl()
        products = acl.list_registered_products()
        grants = get_resource_grant_store()
        _ = grants
        return CheckResult(
            id="tool_acls",
            title="Tool and resource ACLs",
            category="market",
            status="pass",
            summary=f"Tool ACL registry loaded ({len(products)} products).",
            fix_path="/admin/tools",
            docs_path="docs/features/resource-tool-acl.md",
            evidence={"products": products[:20]},
        )
    except Exception as exc:
        return CheckResult(
            id="tool_acls",
            title="Tool and resource ACLs",
            category="market",
            status="fail",
            summary=f"ACL subsystem unavailable: {exc}",
            fix_path="/admin/tools",
        )


def check_client_approval() -> CheckResult:
    try:
        from keprix.security.client_approval.fingerprint import client_approval_enabled

        enabled = client_approval_enabled()
        if enabled:
            return CheckResult(
                id="client_approval",
                title="Remote client approval",
                category="market",
                status="pass",
                summary="Client approval gating is enabled for remote API clients.",
                fix_path="/developer",
                docs_path="docs/features/client-approval-token-security.md",
            )
        return CheckResult(
            id="client_approval",
            title="Remote client approval",
            category="market",
            status="warn",
            summary="Client approval is off. Enable for hosted remote-control surfaces.",
            fix_path="/developer",
            docs_path="docs/features/client-approval-token-security.md",
            evidence={"enabled": False},
        )
    except Exception as exc:
        return CheckResult(
            id="client_approval",
            title="Remote client approval",
            category="market",
            status="unknown",
            summary=f"Could not evaluate client approval: {exc}",
            fix_path="/developer",
        )


def check_self_knowledge() -> CheckResult:
    try:
        from keprix.memory.rag.self_knowledge import SELF_KNOWLEDGE_SOURCE_TYPE, SELF_KNOWLEDGE_USER_ID
        from keprix.memory.rag.indexer import RagIndexer
        import asyncio

        indexer = RagIndexer()

        async def _status() -> dict[str, Any]:
            sources = await indexer.list_sources(SELF_KNOWLEDGE_USER_ID)
            self_sources = [s for s in sources if s.get("source_type") == SELF_KNOWLEDGE_SOURCE_TYPE]
            return {
                "indexed": len(self_sources) > 0,
                "document_count": len(self_sources),
                "total_chunks": sum(int(s.get("chunk_count") or 0) for s in self_sources),
            }

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Avoid nested run; treat as unknown-ish warn with guidance.
                return CheckResult(
                    id="self_knowledge",
                    title="Self-knowledge RAG",
                    category="market",
                    status="warn",
                    summary="Self-knowledge status needs an async context; open Admin > Self-knowledge to verify.",
                    fix_path="/admin/self-knowledge",
                    docs_path="docs/features/rag-pipelines.md",
                )
            status = loop.run_until_complete(_status())
        except RuntimeError:
            status = asyncio.run(_status())

        if status.get("indexed"):
            return CheckResult(
                id="self_knowledge",
                title="Self-knowledge RAG",
                category="market",
                status="pass",
                summary=f"Self-knowledge indexed ({status.get('total_chunks', 0)} chunks).",
                fix_path="/admin/self-knowledge",
                evidence=status,
            )
        return CheckResult(
            id="self_knowledge",
            title="Self-knowledge RAG",
            category="market",
            status="warn",
            summary="Self-knowledge index is empty. Run ingest so the assistant can explain Keprix.",
            fix_path="/admin/self-knowledge",
            docs_path="docs/features/rag-pipelines.md",
            evidence=status,
        )
    except Exception as exc:
        return CheckResult(
            id="self_knowledge",
            title="Self-knowledge RAG",
            category="market",
            status="warn",
            summary=f"Self-knowledge not verified: {exc}",
            fix_path="/admin/self-knowledge",
        )


def check_public_docs() -> CheckResult:
    roots = [
        Path(__file__).resolve().parents[3] / "docs" / "features",
        Path.cwd() / "docs" / "features",
    ]
    required = ["billing.md", "playbooks.md", "migration.md"]
    found_root = next((r for r in roots if r.is_dir()), None)
    if found_root is None:
        return CheckResult(
            id="public_docs",
            title="Public feature docs",
            category="market",
            status="fail",
            summary="docs/features directory not found.",
            fix_path="/developer",
            docs_path="docs/features/migration.md",
        )
    missing = [name for name in required if not (found_root / name).is_file()]
    if missing:
        return CheckResult(
            id="public_docs",
            title="Public feature docs",
            category="market",
            status="fail",
            summary=f"Missing feature docs: {', '.join(missing)}",
            fix_path="/developer",
            evidence={"missing": missing, "root": str(found_root)},
        )
    return CheckResult(
        id="public_docs",
        title="Public feature docs",
        category="market",
        status="pass",
        summary="Core feature docs are present.",
        docs_path="docs/features/migration.md",
        evidence={"root": str(found_root)},
    )


def check_upgrade_package(
    *,
    target_version: str | None = None,
    installability_fn: Callable[[str], Any] | None = None,
) -> CheckResult:
    version = (target_version or os.environ.get("KEPRIX_UPGRADE_TARGET") or "").strip()
    if not version:
        return CheckResult(
            id="upgrade_package",
            title="Upgrade package availability",
            category="upgrade",
            status="warn",
            summary="No upgrade target set. Set KEPRIX_UPGRADE_TARGET or pass target_version to verify installability.",
            fix_path="/settings/upgrade",
            docs_path="docs/features/migration.md",
        )
    try:
        if installability_fn is None:
            from keprix.upgrade.installability import check_target_installable

            result = check_target_installable(version)
        else:
            result = installability_fn(version)
        available = bool(getattr(result, "available", False))
        detail = getattr(result, "detail", "") or ""
        recommendation = getattr(result, "recommendation", "") or ""
        if available:
            return CheckResult(
                id="upgrade_package",
                title="Upgrade package availability",
                category="upgrade",
                status="pass",
                summary=recommendation or f"keprix=={version} is installable.",
                fix_path="/settings/upgrade",
                docs_path="docs/features/migration.md",
                evidence={"version": version, "available": True},
            )
        return CheckResult(
            id="upgrade_package",
            title="Upgrade package availability",
            category="upgrade",
            status="fail",
            summary=recommendation or f"keprix=={version} is not available in the package index.",
            fix_path="/settings/upgrade",
            docs_path="docs/features/migration.md",
            evidence={"version": version, "available": False, "detail": detail[:500]},
        )
    except Exception as exc:
        return CheckResult(
            id="upgrade_package",
            title="Upgrade package availability",
            category="upgrade",
            status="fail",
            summary=f"Upgrade installability check failed: {exc}",
            fix_path="/settings/upgrade",
            evidence={"version": version},
        )


def check_upgrade_backup_path() -> CheckResult:
    """Upgrade must be able to create a backup without hanging."""
    try:
        from keprix.readiness.backup_ops import backup_timeout_sec

        timeout = backup_timeout_sec()
        from keprix.workspace.backup_service import BackupService

        svc = BackupService()
        backup_dir = svc.backup_dir
        writable = backup_dir.exists() and os.access(backup_dir, os.W_OK)
        if not writable:
            return CheckResult(
                id="upgrade_backup_path",
                title="Upgrade backup path",
                category="upgrade",
                status="fail",
                summary=f"Backup directory is not writable: {backup_dir}",
                fix_path="/admin/backup",
                docs_path="docs/operations/backup.md",
                evidence={"backup_dir": str(backup_dir), "timeout_sec": timeout},
            )
        return CheckResult(
            id="upgrade_backup_path",
            title="Upgrade backup path",
            category="upgrade",
            status="pass",
            summary=f"Backup path writable; create timeout {timeout:.0f}s (no hang).",
            fix_path="/admin/backup",
            docs_path="docs/operations/backup.md",
            evidence={"backup_dir": str(backup_dir), "timeout_sec": timeout},
        )
    except Exception as exc:
        return CheckResult(
            id="upgrade_backup_path",
            title="Upgrade backup path",
            category="upgrade",
            status="fail",
            summary=f"Upgrade backup path check failed: {exc}",
            fix_path="/admin/backup",
        )


def check_version_migration() -> CheckResult:
    try:
        from keprix import __version__ as version
    except Exception:
        version = os.environ.get("KEPRIX_VERSION") or "unknown"
    migrations_dir = Path(__file__).resolve().parents[3] / "database" / "migrations"
    if not migrations_dir.is_dir():
        # Alternate layout
        migrations_dir = Path(__file__).resolve().parents[2] / "database" / "migrations"
    count = len(list(migrations_dir.glob("*.sql"))) if migrations_dir.is_dir() else 0
    if count == 0:
        return CheckResult(
            id="version_migration",
            title="Version migrations",
            category="upgrade",
            status="warn",
            summary=f"No SQL migrations found (version={version}). Confirm migration path before upgrade.",
            fix_path="/settings/upgrade",
            docs_path="docs/features/migration.md",
            evidence={"version": version, "migrations": 0},
        )
    return CheckResult(
        id="version_migration",
        title="Version migrations",
        category="upgrade",
        status="pass",
        summary=f"Found {count} migration files (version={version}).",
        fix_path="/settings/upgrade",
        docs_path="docs/features/migration.md",
        evidence={"version": version, "migrations": count, "path": str(migrations_dir)},
    )


def check_backup_creation() -> CheckResult:
    try:
        from keprix.workspace.backup_service import BackupService

        svc = BackupService()
        backups = svc.list_backups()
        if not backups:
            return CheckResult(
                id="backup_creation",
                title="Backup creation",
                category="recovery",
                status="warn",
                summary="No backups recorded yet. Create one from Admin > Backup.",
                fix_path="/admin/backup",
                docs_path="docs/operations/backup.md",
            )
        latest = backups[-1]
        return CheckResult(
            id="backup_creation",
            title="Backup creation",
            category="recovery",
            status="pass",
            summary=f"Latest backup {latest.get('id', '')[:8]} ({latest.get('size_bytes', 0)} bytes).",
            fix_path="/admin/backup",
            evidence={"latest": {k: latest.get(k) for k in ("id", "created_at", "encrypted", "size_bytes")}},
        )
    except Exception as exc:
        return CheckResult(
            id="backup_creation",
            title="Backup creation",
            category="recovery",
            status="fail",
            summary=f"Backup listing failed: {exc}",
            fix_path="/admin/backup",
        )


def check_backup_encryption() -> CheckResult:
    try:
        from keprix.workspace.backup_service import BackupService

        backups = BackupService().list_backups()
        if not backups:
            return CheckResult(
                id="backup_encryption",
                title="Backup encryption",
                category="recovery",
                status="warn",
                summary="No backups to inspect. Prefer password-encrypted backups for production.",
                fix_path="/admin/backup",
                docs_path="docs/operations/backup.md",
            )
        encrypted = [b for b in backups if b.get("encrypted")]
        if encrypted:
            return CheckResult(
                id="backup_encryption",
                title="Backup encryption",
                category="recovery",
                status="pass",
                summary=f"{len(encrypted)}/{len(backups)} backups are encrypted.",
                fix_path="/admin/backup",
                evidence={"encrypted_count": len(encrypted), "total": len(backups)},
            )
        return CheckResult(
            id="backup_encryption",
            title="Backup encryption",
            category="recovery",
            status="warn",
            summary="Backups exist but none are encrypted. Use a password on create for production.",
            fix_path="/admin/backup",
            docs_path="docs/operations/backup.md",
            evidence={"encrypted_count": 0, "total": len(backups)},
        )
    except Exception as exc:
        return CheckResult(
            id="backup_encryption",
            title="Backup encryption",
            category="recovery",
            status="unknown",
            summary=f"Could not evaluate backup encryption: {exc}",
            fix_path="/admin/backup",
        )


def check_backup_retention() -> CheckResult:
    try:
        from keprix.workspace.backup_service import BackupService

        max_keep = int(os.environ.get("KEPRIX_BACKUP_RETENTION_COUNT") or "10")
        backups = BackupService().list_backups()
        if len(backups) > max_keep:
            return CheckResult(
                id="backup_retention",
                title="Backup retention",
                category="recovery",
                status="warn",
                summary=f"{len(backups)} backups exceed retention count {max_keep}. Prune old archives.",
                fix_path="/admin/backup",
                docs_path="docs/operations/backup.md",
                evidence={"count": len(backups), "retention": max_keep},
            )
        return CheckResult(
            id="backup_retention",
            title="Backup retention",
            category="recovery",
            status="pass",
            summary=f"Backup count {len(backups)} within retention {max_keep}.",
            fix_path="/admin/backup",
            evidence={"count": len(backups), "retention": max_keep},
        )
    except Exception as exc:
        return CheckResult(
            id="backup_retention",
            title="Backup retention",
            category="recovery",
            status="unknown",
            summary=f"Could not evaluate retention: {exc}",
            fix_path="/admin/backup",
        )


def check_restore_evidence(store: RestoreEvidenceStore | None = None) -> CheckResult:
    evidence_store = store or get_restore_evidence_store()
    latest = evidence_store.latest()
    if latest is None:
        return CheckResult(
            id="restore_evidence",
            title="Restore test evidence",
            category="recovery",
            status="warn",
            summary="No restore-test evidence recorded. Run a restore drill and record evidence.",
            fix_path="/admin/backup",
            docs_path="docs/operations/backup.md",
            evidence={"has_evidence": False},
        )
    if latest.get("ok"):
        return CheckResult(
            id="restore_evidence",
            title="Restore test evidence",
            category="recovery",
            status="pass",
            summary="Latest restore drill succeeded.",
            fix_path="/admin/backup",
            evidence=latest,
        )
    return CheckResult(
        id="restore_evidence",
        title="Restore test evidence",
        category="recovery",
        status="fail",
        summary="Latest restore drill failed. Fix restore path before relying on backups.",
        fix_path="/admin/backup",
        docs_path="docs/operations/backup.md",
        evidence=latest,
    )


def check_triggers() -> CheckResult:
    try:
        from keprix.triggers.store import get_trigger_store

        store = get_trigger_store()
        triggers = store.list_triggers(limit=5)
        return CheckResult(
            id="triggers",
            title="Trigger builder",
            category="market",
            status="pass",
            summary=f"Trigger builder available ({len(store.list_triggers(limit=500))} triggers).",
            fix_path="/playbooks/triggers",
            docs_path="docs/features/trigger-builder.md",
            evidence={"sample": len(triggers)},
        )
    except Exception as exc:
        return CheckResult(
            id="triggers",
            title="Trigger builder",
            category="market",
            status="warn",
            summary=f"Trigger builder not verified: {exc}",
            fix_path="/playbooks/triggers",
        )
