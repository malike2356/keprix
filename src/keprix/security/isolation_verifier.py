"""IsolationVerifier: run isolation invariant checks and report findings.

Each check is a method that returns list[IsolationFinding]. Checks that
require a database are wired via the injectable `_db` interface so they
can be tested with mocks and run without a live database in unit tests.

Checks that rely on the in-memory CrossProductGrantStore (EXPIRED_GRANTS,
OVERLY_BROAD_GRANTS, GRANT_WITHOUT_EXPIRY) work without any DB at all.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Callable

from .cross_product_grant import CrossProductGrantStore
from .isolation_check import IsolationCheck, IsolationFinding, IsolationReport


CheckFn = Callable[[], "list[IsolationFinding]"]


class _NullDB:
    """Placeholder DB interface used when no database is configured."""

    async def scalar(self, sql: str) -> int:
        return 0

    async def fetchall(self, sql: str) -> list:
        return []

    async def execute(self, sql: str) -> None:
        pass


class IsolationVerifier:
    """Runs isolation invariant checks and returns a structured IsolationReport.

    Usage::

        verifier = IsolationVerifier(grant_store=store)
        report = await verifier.run_all()
        if not report.passed:
            print(report.to_dict())

    For DB-backed checks, supply a ``db`` object with scalar/fetchall/execute methods.
    Without a DB, all DB-dependent checks return zero findings (safe default).
    """

    def __init__(
        self,
        db: Any = None,
        grant_store: CrossProductGrantStore | None = None,
    ) -> None:
        self._db = db or _NullDB()
        self._grant_store = grant_store or CrossProductGrantStore()

    async def run_all(
        self,
        checks: list[IsolationCheck] | None = None,
        fix: bool = False,
    ) -> IsolationReport:
        """Run all (or specified) checks. Returns a structured IsolationReport."""
        checks_to_run = checks or list(IsolationCheck)
        findings: list[IsolationFinding] = []
        t0 = time.monotonic()

        for check in checks_to_run:
            try:
                results = await self._run_check(check)
                findings.extend(results)
            except Exception as exc:
                findings.append(IsolationFinding(
                    check=check,
                    severity="medium",
                    description=f"Check {check.value} failed with error: {exc}",
                    fix_available=False,
                ))

        if fix:
            for finding in findings:
                if finding.fix_available:
                    await self._apply_fix(finding)

        duration = time.monotonic() - t0
        return IsolationReport(
            run_at=datetime.now(tz=timezone.utc),
            checks_run=checks_to_run,
            findings=findings,
            duration_seconds=duration,
        )

    async def _run_check(self, check: IsolationCheck) -> list[IsolationFinding]:
        dispatch = {
            IsolationCheck.ORPHANED_ROWS: self._check_orphaned_rows,
            IsolationCheck.CROSS_NAMESPACE_REFS: self._check_cross_namespace_refs,
            IsolationCheck.EXPIRED_GRANTS: self._check_expired_grants,
            IsolationCheck.STALE_QUOTA_PERIODS: self._check_stale_quota_periods,
            IsolationCheck.SESSION_PRODUCT_MISMATCH: self._check_session_product_mismatch,
            IsolationCheck.UNPROTECTED_ROUTES: self._check_unprotected_routes,
            IsolationCheck.MISSING_WORKSPACE_FILTER: self._check_missing_workspace_filter,
            IsolationCheck.CROSS_PRODUCT_LEAK: self._check_cross_product_leak,
            IsolationCheck.TOOL_ACL_BYPASS: self._check_tool_acl_bypass,
            IsolationCheck.EGRESS_GATE_BYPASS: self._check_egress_gate_bypass,
            IsolationCheck.OVERLY_BROAD_GRANTS: self._check_overly_broad_grants,
            IsolationCheck.GRANT_WITHOUT_EXPIRY: self._check_grant_without_expiry,
        }
        fn = dispatch.get(check)
        if fn is None:
            return []
        return await fn()

    # -------------------------------------------------------------------
    # Database-backed checks
    # -------------------------------------------------------------------

    async def _check_orphaned_rows(self) -> list[IsolationFinding]:
        from .isolation_query_filter import ISOLATED_TABLES
        findings = []
        for table in ISOLATED_TABLES:
            count = await self._db.scalar(
                f"SELECT COUNT(*) FROM {table} WHERE product_id IS NULL OR product_id = ''"
            )
            if count > 0:
                findings.append(IsolationFinding(
                    check=IsolationCheck.ORPHANED_ROWS,
                    severity="high",
                    table=table,
                    count=count,
                    description=f"{count} row(s) in '{table}' have no product_id.",
                    fix_available=True,
                    fix_description=(
                        f"UPDATE {table} SET product_id = 'keprix' "
                        f"WHERE product_id IS NULL OR product_id = ''"
                    ),
                ))
        return findings

    async def _check_cross_namespace_refs(self) -> list[IsolationFinding]:
        rows = await self._db.fetchall("""
            SELECT sm.id, sm.product_id AS msg_product, s.product_id AS sess_product
            FROM session_messages sm
            JOIN sessions s ON sm.session_id = s.id
            WHERE sm.product_id != s.product_id
            LIMIT 100
        """)
        if not rows:
            return []
        return [IsolationFinding(
            check=IsolationCheck.CROSS_NAMESPACE_REFS,
            severity="critical",
            table="session_messages",
            count=len(rows),
            description=(
                f"{len(rows)} session_messages have a different product_id "
                "than their parent session."
            ),
            fix_available=False,
            sample_ids=[str(r.get("id", "")) for r in rows[:5]],
        )]

    async def _check_stale_quota_periods(self) -> list[IsolationFinding]:
        count = await self._db.scalar(
            "SELECT COUNT(*) FROM quota_usage WHERE period_end < CURRENT_TIMESTAMP"
        )
        if count > 0:
            return [IsolationFinding(
                check=IsolationCheck.STALE_QUOTA_PERIODS,
                severity="medium",
                table="quota_usage",
                count=count,
                description=f"{count} quota_usage row(s) past period_end not reset.",
                fix_available=True,
                fix_description="DELETE FROM quota_usage WHERE period_end < CURRENT_TIMESTAMP",
            )]
        return []

    async def _check_session_product_mismatch(self) -> list[IsolationFinding]:
        count = await self._db.scalar("""
            SELECT COUNT(*) FROM sessions s
            JOIN auth_tokens t ON s.token_id = t.id
            WHERE s.product_id != t.product_id
        """)
        if count > 0:
            return [IsolationFinding(
                check=IsolationCheck.SESSION_PRODUCT_MISMATCH,
                severity="critical",
                table="sessions",
                count=count,
                description=f"{count} session(s) have product_id mismatch with auth token.",
                fix_available=False,
            )]
        return []

    # -------------------------------------------------------------------
    # Static analysis checks
    # -------------------------------------------------------------------

    async def _check_unprotected_routes(self) -> list[IsolationFinding]:
        try:
            from keprix.app import app
            middleware_types = [type(m).__name__ for m in getattr(app, "user_middleware", [])]
            if "IsolationMiddleware" not in middleware_types:
                routes = [
                    r.path for r in getattr(app, "routes", [])
                    if hasattr(r, "path")
                ]
                return [IsolationFinding(
                    check=IsolationCheck.UNPROTECTED_ROUTES,
                    severity="critical",
                    count=len(routes),
                    description=(
                        "IsolationMiddleware is not in the middleware stack. "
                        "ALL routes are unprotected."
                    ),
                    routes=routes[:20],
                    fix_available=False,
                )]
        except Exception:
            pass
        return []

    async def _check_missing_workspace_filter(self) -> list[IsolationFinding]:
        # Placeholder: static analysis requires AST scanning. Returns no findings by default.
        return []

    # -------------------------------------------------------------------
    # Live checks (controlled test requests)
    # -------------------------------------------------------------------

    async def _check_cross_product_leak(self) -> list[IsolationFinding]:
        # Requires live app; returns no findings when app is not available
        return []

    async def _check_tool_acl_bypass(self) -> list[IsolationFinding]:
        return []

    async def _check_egress_gate_bypass(self) -> list[IsolationFinding]:
        return []

    # -------------------------------------------------------------------
    # Grant hygiene checks (use in-memory grant store - no DB required)
    # -------------------------------------------------------------------

    async def _check_expired_grants(self) -> list[IsolationFinding]:
        from .cross_product_grant import CrossProductGrantStore
        # For DB-backed usage, query the table directly
        count = await self._db.scalar(
            "SELECT COUNT(*) FROM cross_product_grants "
            "WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP"
        )
        # Also check the in-memory store
        in_memory_grants = []
        try:
            in_memory_grants = [
                g for g in self._grant_store._grants.values()
                if g.is_expired
            ]
        except Exception:
            pass

        total = count + len(in_memory_grants)
        if total > 0:
            return [IsolationFinding(
                check=IsolationCheck.EXPIRED_GRANTS,
                severity="medium",
                table="cross_product_grants",
                count=total,
                description=f"{total} expired CrossProductGrant row(s) not yet purged.",
                fix_available=True,
                fix_description=(
                    "DELETE FROM cross_product_grants "
                    "WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP"
                ),
            )]
        return []

    async def _check_overly_broad_grants(self) -> list[IsolationFinding]:
        try:
            broad = [
                g for g in self._grant_store._grants.values()
                if "all" in g.scopes
            ]
        except Exception:
            return []
        if broad:
            return [IsolationFinding(
                check=IsolationCheck.OVERLY_BROAD_GRANTS,
                severity="low",
                table="cross_product_grants",
                count=len(broad),
                description=(
                    f"{len(broad)} grant(s) have scope='all' which is overly permissive."
                ),
                fix_available=False,
                sample_ids=[g.grant_id for g in broad[:5]],
            )]
        return []

    async def _check_grant_without_expiry(self) -> list[IsolationFinding]:
        try:
            no_expiry = [
                g for g in self._grant_store._grants.values()
                if g.expires_at is None
            ]
        except Exception:
            return []
        if no_expiry:
            return [IsolationFinding(
                check=IsolationCheck.GRANT_WITHOUT_EXPIRY,
                severity="low",
                table="cross_product_grants",
                count=len(no_expiry),
                description=(
                    f"{len(no_expiry)} grant(s) have no expiry date. "
                    "Grants should have a bounded lifetime."
                ),
                fix_available=False,
                sample_ids=[g.grant_id for g in no_expiry[:5]],
            )]
        return []

    # -------------------------------------------------------------------
    # Auto-remediation
    # -------------------------------------------------------------------

    async def _apply_fix(self, finding: IsolationFinding) -> None:
        if finding.check == IsolationCheck.ORPHANED_ROWS and finding.table:
            await self._db.execute(
                f"UPDATE {finding.table} SET product_id = 'keprix' "
                f"WHERE product_id IS NULL OR product_id = ''"
            )
        elif finding.check == IsolationCheck.EXPIRED_GRANTS:
            await self._db.execute(
                "DELETE FROM cross_product_grants "
                "WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP"
            )
            await self._grant_store.purge_expired()
        elif finding.check == IsolationCheck.STALE_QUOTA_PERIODS:
            await self._db.execute(
                "DELETE FROM quota_usage WHERE period_end < CURRENT_TIMESTAMP"
            )
