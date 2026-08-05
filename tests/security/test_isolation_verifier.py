"""Tests for security/isolation_verifier.py."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from keprix.security.cross_product_grant import CrossProductGrant, CrossProductGrantStore
from keprix.security.isolation_check import IsolationCheck, IsolationFinding, IsolationReport
from keprix.security.isolation_verifier import IsolationVerifier


def _grant(grant_id="g1", expires_at=None, scopes=None):
    return CrossProductGrant(
        grant_id=grant_id,
        grantor_product_id="aiva",
        grantee_product_id="abbis",
        resource_kind="document",
        resource_id="doc-1",
        workspace_id="ws-1",
        granted_by="user-1",
        expires_at=expires_at,
        scopes=scopes or ["read"],
    )


def _make_db(scalar_return=0, fetchall_return=None):
    db = MagicMock()
    db.scalar = AsyncMock(return_value=scalar_return)
    db.fetchall = AsyncMock(return_value=fetchall_return or [])
    db.execute = AsyncMock()
    return db


@pytest.fixture
def verifier():
    return IsolationVerifier()


@pytest.fixture
def verifier_with_db():
    return IsolationVerifier(db=_make_db())


@pytest.mark.asyncio
async def test_run_all_returns_report(verifier):
    report = await verifier.run_all()
    assert isinstance(report, IsolationReport)
    assert isinstance(report.run_at, datetime)
    assert isinstance(report.checks_run, list)
    assert isinstance(report.findings, list)


@pytest.mark.asyncio
async def test_run_all_subset_of_checks(verifier):
    checks = [IsolationCheck.EXPIRED_GRANTS, IsolationCheck.GRANT_WITHOUT_EXPIRY]
    report = await verifier.run_all(checks=checks)
    assert set(report.checks_run) == set(checks)


@pytest.mark.asyncio
async def test_report_passed_when_no_critical_or_high(verifier):
    report = await verifier.run_all()
    # With null DB and empty grant store: no findings at all
    assert report.passed


@pytest.mark.asyncio
async def test_report_fails_on_critical_finding():
    store = CrossProductGrantStore()
    verifier = IsolationVerifier(db=_make_db(fetchall_return=[{"id": "1", "msg_product": "a", "sess_product": "b"}]))
    report = await verifier.run_all(checks=[IsolationCheck.CROSS_NAMESPACE_REFS])
    assert not report.passed
    assert any(f.severity == "critical" for f in report.findings)


@pytest.mark.asyncio
async def test_orphaned_rows_finding(verifier):
    db = _make_db(scalar_return=5)
    v = IsolationVerifier(db=db)
    report = await v.run_all(checks=[IsolationCheck.ORPHANED_ROWS])
    assert len(report.findings) > 0
    finding = report.findings[0]
    assert finding.check == IsolationCheck.ORPHANED_ROWS
    assert finding.severity == "high"
    assert finding.fix_available
    assert finding.count == 5


@pytest.mark.asyncio
async def test_no_orphaned_rows_no_finding():
    db = _make_db(scalar_return=0)
    v = IsolationVerifier(db=db)
    report = await v.run_all(checks=[IsolationCheck.ORPHANED_ROWS])
    assert report.findings == []


@pytest.mark.asyncio
async def test_expired_grants_from_grant_store():
    store = CrossProductGrantStore()
    await store.add(_grant(grant_id="old", expires_at=time.time() - 1))
    v = IsolationVerifier(grant_store=store)
    report = await v.run_all(checks=[IsolationCheck.EXPIRED_GRANTS])
    assert any(f.check == IsolationCheck.EXPIRED_GRANTS for f in report.findings)
    finding = next(f for f in report.findings if f.check == IsolationCheck.EXPIRED_GRANTS)
    assert finding.count >= 1


@pytest.mark.asyncio
async def test_grant_without_expiry_flagged():
    store = CrossProductGrantStore()
    await store.add(_grant(expires_at=None))   # no expiry
    v = IsolationVerifier(grant_store=store)
    report = await v.run_all(checks=[IsolationCheck.GRANT_WITHOUT_EXPIRY])
    assert any(f.check == IsolationCheck.GRANT_WITHOUT_EXPIRY for f in report.findings)


@pytest.mark.asyncio
async def test_grant_with_expiry_not_flagged():
    store = CrossProductGrantStore()
    await store.add(_grant(expires_at=time.time() + 3600))   # future expiry
    v = IsolationVerifier(grant_store=store)
    report = await v.run_all(checks=[IsolationCheck.GRANT_WITHOUT_EXPIRY])
    assert not any(f.check == IsolationCheck.GRANT_WITHOUT_EXPIRY for f in report.findings)


@pytest.mark.asyncio
async def test_overly_broad_grants_flagged():
    store = CrossProductGrantStore()
    await store.add(_grant(scopes=["all"]))
    v = IsolationVerifier(grant_store=store)
    report = await v.run_all(checks=[IsolationCheck.OVERLY_BROAD_GRANTS])
    assert any(f.check == IsolationCheck.OVERLY_BROAD_GRANTS for f in report.findings)


@pytest.mark.asyncio
async def test_fix_expired_grants():
    store = CrossProductGrantStore()
    await store.add(_grant(grant_id="expired", expires_at=time.time() - 1))
    db = _make_db()
    v = IsolationVerifier(db=db, grant_store=store)
    await v.run_all(checks=[IsolationCheck.EXPIRED_GRANTS], fix=True)
    # Purge should have been called
    assert "expired" not in store._grants


@pytest.mark.asyncio
async def test_isolation_report_summary():
    findings = [
        IsolationFinding(IsolationCheck.ORPHANED_ROWS, "high", "5 orphaned", fix_available=True, count=5),
        IsolationFinding(IsolationCheck.EXPIRED_GRANTS, "medium", "2 expired", fix_available=True, count=2),
    ]
    report = IsolationReport(
        run_at=datetime.now(tz=timezone.utc),
        checks_run=[IsolationCheck.ORPHANED_ROWS, IsolationCheck.EXPIRED_GRANTS],
        findings=findings,
    )
    assert not report.passed   # high severity makes it fail
    assert report.summary["total_findings"] == 2
    assert report.summary["by_severity"]["high"] == 1
    assert report.summary["by_severity"]["medium"] == 1


def test_finding_to_dict():
    f = IsolationFinding(
        check=IsolationCheck.ORPHANED_ROWS,
        severity="high",
        description="5 orphaned rows",
        fix_available=True,
        count=5,
        table="memories",
    )
    d = f.to_dict()
    assert d["check"] == "orphaned_rows"
    assert d["severity"] == "high"
    assert d["count"] == 5
    assert d["fix_available"] is True


@pytest.mark.asyncio
async def test_report_duration_recorded(verifier):
    report = await verifier.run_all(checks=[IsolationCheck.GRANT_WITHOUT_EXPIRY])
    assert report.duration_seconds >= 0.0
