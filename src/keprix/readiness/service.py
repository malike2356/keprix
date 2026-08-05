"""Canonical readiness report service."""

from __future__ import annotations

from typing import Any, Callable

from keprix.readiness import checks as check_fns
from keprix.readiness.models import (
    CheckCategory,
    CheckResult,
    ReadinessReport,
    count_statuses,
    rollup,
    utcnow_iso,
)
from keprix.readiness.restore_evidence import RestoreEvidenceStore


def _default_checks(
    *,
    target_version: str | None = None,
    installability_fn: Callable[[str], Any] | None = None,
    load_billing_config: Callable[[], Any] | None = None,
    restore_store: RestoreEvidenceStore | None = None,
) -> list[CheckResult]:
    return [
        check_fns.check_auth(),
        check_fns.check_billing_prices(load_config=load_billing_config),
        check_fns.check_byok_and_wallet(),
        check_fns.check_quotas(),
        check_fns.check_tool_acls(),
        check_fns.check_client_approval(),
        check_fns.check_self_knowledge(),
        check_fns.check_public_docs(),
        check_fns.check_triggers(),
        check_fns.check_upgrade_package(target_version=target_version, installability_fn=installability_fn),
        check_fns.check_upgrade_backup_path(),
        check_fns.check_version_migration(),
        check_fns.check_backup_creation(),
        check_fns.check_backup_encryption(),
        check_fns.check_backup_retention(),
        check_fns.check_restore_evidence(store=restore_store),
    ]


def build_report(
    check_results: list[CheckResult] | None = None,
    *,
    target_version: str | None = None,
    installability_fn: Callable[[str], Any] | None = None,
    load_billing_config: Callable[[], Any] | None = None,
    restore_store: RestoreEvidenceStore | None = None,
) -> ReadinessReport:
    results = check_results or _default_checks(
        target_version=target_version,
        installability_fn=installability_fn,
        load_billing_config=load_billing_config,
        restore_store=restore_store,
    )

    def _cat(cat: CheckCategory) -> list[CheckResult]:
        return [c for c in results if c.category == cat]

    market = rollup([c.status for c in _cat("market")])
    upgrade = rollup([c.status for c in _cat("upgrade")])
    recovery = rollup([c.status for c in _cat("recovery")])
    overall = rollup([market, upgrade, recovery])
    notes = [
        "Community Edition coffee donation is voluntary and never blocks readiness.",
        "Failed checks include a fix_path for admin UI navigation.",
    ]
    return ReadinessReport(
        generated_at=utcnow_iso(),
        overall=overall,
        market=market,
        upgrade=upgrade,
        recovery=recovery,
        checks=results,
        counts=count_statuses(results),
        notes=notes,
    )


def run_readiness(**kwargs: Any) -> dict[str, Any]:
    return build_report(**kwargs).to_dict()
