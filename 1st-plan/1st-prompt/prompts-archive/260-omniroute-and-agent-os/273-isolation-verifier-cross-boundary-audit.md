# Keprix - Prompt 259: Isolation Verifier and Cross-Boundary Audit

## Context

Prompts 255-258 build the enforcement layers: namespace isolation middleware, tool ACL,
network egress policy, and resource quotas. Enforcement without verification is wishful
thinking. A migration bug could leave 10,000 memory rows with `product_id = NULL`. A
new route added by a developer could forget to register with the isolation middleware.
A CrossProductGrant that expired two months ago could still be granting access because
the cleanup job never ran.

This prompt adds the audit layer: a continuous scanner that verifies the invariants
defined in Prompt 255 are actually holding, and a CLI command that lets operators run
a one-off isolation health check. This is the OS equivalent of a filesystem integrity
checker, running periodically to confirm that the security kernel is in the state it
claims to be in.

## What already exists (do not rebuild)

- `security/product_context.py` -- `get_product_context()` from Prompt 255
- `security/isolation_middleware.py` -- isolation enforcement from Prompt 255
- `security/tool_acl.py` -- tool ACL from Prompt 256
- `security/egress_policy.py` and `egress_gate.py` -- egress enforcement from Prompt 257
- `quotas/quota_enforcer.py` -- quota enforcement from Prompt 258
- `data_architecture/` -- data plane and schema definitions
- Scout monitoring client (referenced in Prompt 255 `isolation_violation_handler`)

## What the verifier checks

The verifier runs a suite of invariant checks. Each check is independent and can be
run alone or as a group.

```python
class IsolationCheck(StrEnum):
    # Data integrity checks (query the DB directly, not through ORM)
    ORPHANED_ROWS         = "orphaned_rows"        # rows with product_id = NULL
    CROSS_NAMESPACE_REFS  = "cross_namespace_refs" # FK references across product boundaries
    EXPIRED_GRANTS        = "expired_grants"        # CrossProductGrant rows past expires_at
    STALE_QUOTA_PERIODS   = "stale_quota_periods"  # quota_usage rows past period_end not reset
    SESSION_PRODUCT_MISMATCH = "session_product_mismatch"  # session product_id != auth token

    # Route coverage checks (static analysis of the API surface)
    UNPROTECTED_ROUTES    = "unprotected_routes"   # FastAPI routes not wrapped by IsolationMiddleware
    MISSING_WORKSPACE_FILTER = "missing_ws_filter" # query patterns not filtered by workspace_id

    # Live checks (spawn a controlled test request)
    CROSS_PRODUCT_LEAK    = "cross_product_leak"   # request as product A returns product B data
    TOOL_ACL_BYPASS       = "tool_acl_bypass"      # denied tool callable through a different path
    EGRESS_GATE_BYPASS    = "egress_gate_bypass"   # request reaches a denied host

    # Grant hygiene
    OVERLY_BROAD_GRANTS   = "overly_broad_grants"  # grants with scope="all" (should be rare)
    GRANT_WITHOUT_EXPIRY  = "grant_without_expiry" # grants with expires_at = NULL
```

## What to build

### 1. Isolation check runner

`src/keprix/security/isolation_verifier.py`:

```python
class IsolationVerifier:
    """
    Runs isolation invariant checks and returns structured findings.
    Each check is a method that returns a list of IsolationFinding.
    """

    async def run_all(
        self,
        checks: list[IsolationCheck] | None = None,
        fix: bool = False,
    ) -> IsolationReport:
        """
        Run all (or specified) checks. If fix=True, attempt auto-remediation
        for safe-to-fix issues (orphaned rows, expired grants).
        """
        checks = checks or list(IsolationCheck)
        results: list[IsolationFinding] = []

        for check in checks:
            findings = await self._run_check(check)
            results.extend(findings)

        return IsolationReport(
            run_at=utcnow(),
            checks_run=checks,
            findings=results,
            summary=self._summarise(results),
        )

    async def _check_orphaned_rows(self) -> list[IsolationFinding]:
        """
        Find rows in isolated tables with product_id IS NULL or product_id = ''.
        These are rows that bypassed the isolation migration or were inserted
        outside the isolation middleware context.
        """
        findings = []
        for table in IsolationQueryFilter.ISOLATED_TABLES:
            count = await self._db.scalar(
                f"SELECT COUNT(*) FROM {table} WHERE product_id IS NULL OR product_id = ''"
            )
            if count > 0:
                findings.append(IsolationFinding(
                    check=IsolationCheck.ORPHANED_ROWS,
                    severity="high",
                    table=table,
                    count=count,
                    description=f"{count} rows in `{table}` have no product_id.",
                    fix_available=True,
                    fix_description=f"UPDATE {table} SET product_id = 'keprix' WHERE product_id IS NULL",
                ))
        return findings

    async def _check_cross_namespace_refs(self) -> list[IsolationFinding]:
        """
        Find foreign key references that cross product boundaries.
        Example: a session_message row with product_id = 'aiva' pointing to
        a session with product_id = 'abbis'.
        """
        findings = []
        # session_messages.session_id -> sessions.id cross-product
        rows = await self._db.fetchall("""
            SELECT sm.id, sm.product_id as msg_product, s.product_id as sess_product
            FROM session_messages sm
            JOIN sessions s ON sm.session_id = s.id
            WHERE sm.product_id != s.product_id
            LIMIT 100
        """)
        if rows:
            findings.append(IsolationFinding(
                check=IsolationCheck.CROSS_NAMESPACE_REFS,
                severity="critical",
                table="session_messages",
                count=len(rows),
                description=(
                    f"{len(rows)} session_messages have a different product_id than their parent session. "
                    f"This indicates data written outside the isolation middleware."
                ),
                fix_available=False,
                sample_ids=[r["id"] for r in rows[:5]],
            ))
        return findings

    async def _check_expired_grants(self) -> list[IsolationFinding]:
        """
        CrossProductGrant rows where expires_at < NOW() are still in the table.
        They should have been deleted by the cleanup job.
        """
        count = await self._db.scalar("""
            SELECT COUNT(*) FROM cross_product_grants
            WHERE expires_at IS NOT NULL AND expires_at < NOW()
        """)
        if count > 0:
            return [IsolationFinding(
                check=IsolationCheck.EXPIRED_GRANTS,
                severity="medium",
                table="cross_product_grants",
                count=count,
                description=f"{count} expired CrossProductGrant rows not yet deleted.",
                fix_available=True,
                fix_description="DELETE FROM cross_product_grants WHERE expires_at < NOW()",
            )]
        return []

    async def _check_unprotected_routes(self) -> list[IsolationFinding]:
        """
        Static analysis: find FastAPI routes not wrapped by IsolationMiddleware.
        Walks the router to find all registered routes and checks if the
        isolation middleware is in the app's middleware stack.
        If it is, all routes are protected. If not, list all routes as unprotected.
        """
        from keprix.app import app
        middleware_types = [type(m).__name__ for m in app.user_middleware]
        if "IsolationMiddleware" not in middleware_types:
            routes = [r.path for r in app.routes if hasattr(r, "path")]
            return [IsolationFinding(
                check=IsolationCheck.UNPROTECTED_ROUTES,
                severity="critical",
                count=len(routes),
                description="IsolationMiddleware is not in the middleware stack. ALL routes are unprotected.",
                routes=routes[:20],
                fix_available=False,
            )]
        return []

    async def _check_cross_product_leak(self) -> list[IsolationFinding]:
        """
        Live check: make a real HTTP request authenticated as product 'aiva' and
        verify that no memories/sessions/skills owned by 'abbis' appear in the response.
        Uses the internal test client (no external network call).
        """
        from keprix.tests.isolation_fixtures import create_isolated_test_data
        async with TestClient(app) as client:
            # Write a memory as product 'abbis'
            abbis_memory_id = await create_isolated_test_data(product_id="abbis")

            # Read memories as product 'aiva' -- should NOT see abbis memory
            resp = await client.get(
                "/api/memories",
                headers={"X-Keprix-Product": "aiva", "Authorization": "Bearer test-token-aiva"}
            )
            body = resp.json()
            returned_ids = {m["id"] for m in body.get("memories", [])}

            if abbis_memory_id in returned_ids:
                return [IsolationFinding(
                    check=IsolationCheck.CROSS_PRODUCT_LEAK,
                    severity="critical",
                    description=(
                        f"Memory {abbis_memory_id} (owned by 'abbis') was returned in "
                        f"response to a request authenticated as 'aiva'. Namespace isolation is BROKEN."
                    ),
                    fix_available=False,
                )]
        return []
```

```python
@dataclass
class IsolationFinding:
    check: IsolationCheck
    severity: str           # "critical" | "high" | "medium" | "low"
    description: str
    fix_available: bool
    count: int = 0
    table: str | None = None
    sample_ids: list[str] = field(default_factory=list)
    fix_description: str | None = None
    routes: list[str] = field(default_factory=list)

@dataclass
class IsolationReport:
    run_at: datetime
    checks_run: list[IsolationCheck]
    findings: list[IsolationFinding]
    summary: dict
    passed: bool = field(init=False)

    def __post_init__(self):
        self.passed = not any(
            f.severity in ("critical", "high") for f in self.findings
        )
```

### 2. Auto-remediation

For findings marked `fix_available=True`, the verifier can apply safe fixes:

```python
async def _apply_fix(self, finding: IsolationFinding):
    """
    Safe auto-remediations only:
    - Set product_id = 'keprix' on orphaned rows (safer than deleting)
    - Delete expired grants (idempotent, not data loss)
    - Reset stale quota periods (accounting cleanup)

    Never auto-fix: cross-namespace FK references, route coverage gaps,
    live leak findings. Those require human review.
    """
    if finding.check == IsolationCheck.ORPHANED_ROWS:
        await self._db.execute(
            f"UPDATE {finding.table} SET product_id = 'keprix' "
            f"WHERE product_id IS NULL OR product_id = ''"
        )
    elif finding.check == IsolationCheck.EXPIRED_GRANTS:
        await self._db.execute(
            "DELETE FROM cross_product_grants WHERE expires_at < NOW()"
        )
```

### 3. CLI command

```
keprix audit --isolation [options]

Options:
  --check <name>      Run a specific check only (repeatable)
  --fix               Apply safe auto-remediations after the run
  --output <format>   text (default) | json | csv
  --severity <level>  Only report findings at this severity or above
  --quiet             Exit-code only (0=pass, 1=findings, 2=error)
```

Example output:

```
keprix audit --isolation

Isolation Audit  -  2026-07-02T14:03:00Z
=========================================

Checks run: 11
Findings: 3 (1 critical, 1 high, 1 medium)
Status: FAIL

CRITICAL  cross_product_leak
  Memory mem_abc123 (owned by 'abbis') was returned in response to a request
  authenticated as 'aiva'. Namespace isolation is BROKEN.
  Fix: investigate IsolationQueryFilter event listener registration.

HIGH      orphaned_rows
  table: session_messages  count: 47
  47 rows in `session_messages` have no product_id.
  Fix available: keprix audit --isolation --fix

MEDIUM    expired_grants
  table: cross_product_grants  count: 12
  12 expired CrossProductGrant rows not yet deleted.
  Fix available: keprix audit --isolation --fix

Run 'keprix audit --isolation --fix' to apply 2 safe auto-remediations.
CRITICAL finding requires manual investigation.
```

```
keprix audit --isolation --fix

Applying 2 safe remediations...
  OK  orphaned_rows  -- 47 rows updated (product_id set to 'keprix')
  OK  expired_grants -- 12 rows deleted

Re-running checks...
Findings: 1 (1 critical)
Status: FAIL (manual review required)
```

### 4. Continuous monitor

`src/keprix/security/isolation_monitor.py`:

Run on a schedule (default: every 6 hours). Publishes results to the Scout monitoring
client and the admin dashboard.

```python
class IsolationMonitor:
    """
    Scheduled runner for isolation checks. Emits alerts on new findings.
    Tracks finding history so repeat findings are de-duplicated.
    """

    async def run_scheduled(self):
        verifier = IsolationVerifier()
        report = await verifier.run_all(
            checks=[
                # Skip live checks in scheduled mode (performance impact)
                IsolationCheck.ORPHANED_ROWS,
                IsolationCheck.CROSS_NAMESPACE_REFS,
                IsolationCheck.EXPIRED_GRANTS,
                IsolationCheck.STALE_QUOTA_PERIODS,
                IsolationCheck.UNPROTECTED_ROUTES,
                IsolationCheck.GRANT_WITHOUT_EXPIRY,
                IsolationCheck.OVERLY_BROAD_GRANTS,
            ]
        )
        await self._store_report(report)
        await self._emit_alerts(report)

    async def _emit_alerts(self, report: IsolationReport):
        for finding in report.findings:
            if finding.severity == "critical":
                await scout_client.alert(
                    event="isolation_finding",
                    severity="critical",
                    check=finding.check,
                    description=finding.description,
                    count=finding.count,
                )
            elif finding.severity == "high" and not self._was_alerted_recently(finding):
                await scout_client.alert(event="isolation_finding", severity="warning", ...)
```

Cron schedule in `config.yaml`:
```yaml
isolation_monitor:
  enabled: true
  schedule: "0 */6 * * *"   # every 6 hours
  live_checks_schedule: "0 2 * * *"   # nightly at 02:00 (includes cross_product_leak, etc.)
  alert_on: ["critical", "high"]
  auto_fix: false            # set true to auto-remediate safe findings on schedule
```

### 5. Audit dashboard

Route: `/admin/isolation-audit`

```
Isolation Audit Dashboard
==========================

Last run: 2026-07-02 14:00 UTC  [Run now]  [Run with --fix]

Status: PASS  (no findings in last 6 hours)

History:
  2026-07-02 14:00  PASS   0 findings
  2026-07-01 08:00  PASS   0 findings
  2026-06-30 14:00  WARN   1 medium (expired grants - auto-fixed)
  2026-06-29 08:00  FAIL   1 critical (orphaned rows - fixed manually)

Checks enabled:
  orphaned_rows               PASS (0 rows)
  cross_namespace_refs        PASS
  expired_grants              PASS (0 rows)
  unprotected_routes          PASS (IsolationMiddleware active)
  grant_without_expiry        PASS
  overly_broad_grants         PASS

Live checks (run nightly):
  cross_product_leak          PASS (last: 2026-07-02 02:00)
  tool_acl_bypass             PASS
  egress_gate_bypass          PASS

Active CrossProductGrants: 2
  ws_abc  aiva -> abbis  document:doc_xyz  scope:read  expires: 2026-08-01
  ws_def  abbis -> keprix  skill:skill_report  scope:read  never expires  [WARNING: no expiry]
```

### 6. Grant hygiene enforcement

In addition to detecting overly broad grants, the verifier enforces a grace period
policy: no CrossProductGrant may lack an `expires_at` unless it was explicitly approved
by a workspace administrator with a reason on record.

```python
class GrantHygieneEnforcer:
    """
    Called when a CrossProductGrant is created. Rejects grants that violate
    hygiene rules unless the admin provides an override reason.
    """

    async def validate_grant(self, grant: CrossProductGrant, admin_override: str | None = None):
        if grant.expires_at is None and admin_override is None:
            raise GrantHygieneViolation(
                "CrossProductGrant must have an expiry date. "
                "To create a permanent grant, provide an admin_override reason."
            )
        if "all" in grant.scopes and admin_override is None:
            raise GrantHygieneViolation(
                "CrossProductGrant with scope='all' requires an admin_override reason."
            )
```

## Files to create

```
src/keprix/security/
  isolation_verifier.py      - IsolationVerifier, IsolationFinding, IsolationReport
  isolation_monitor.py       - IsolationMonitor (scheduled runner, Scout alerts)
  grant_hygiene_enforcer.py  - GrantHygieneEnforcer

src/keprix/tests/
  isolation_fixtures.py      - test data helpers used by live check (_check_cross_product_leak)

src/keprix/cli/
  audit_isolation.py         - keprix audit --isolation command

src/keprix/api/
  isolation_audit_routes.py  - GET /api/admin/isolation-audit (reports + history)
                               POST /api/admin/isolation-audit/run (trigger run)

frontend/src/app/(admin)/dashboard/
  isolation-audit/
    page.tsx                 - isolation audit dashboard

New DB table: isolation_audit_reports
  id, run_at, checks_run, findings_json, passed, created_at

migrations/
  add_isolation_audit_reports_table.py
```

## Acceptance criteria

- `keprix audit --isolation` runs all 11 checks and exits 0 when no findings exist.
- `keprix audit --isolation` exits 1 when findings exist and prints them with severity.
- `keprix audit --isolation --fix` resolves orphaned_rows and expired_grants findings
  without human intervention, then re-runs checks to confirm resolution.
- `_check_cross_product_leak` correctly detects when a memory written by 'abbis' leaks
  into an 'aiva' response. It returns PASS when isolation is working correctly.
- `_check_unprotected_routes` detects when IsolationMiddleware is absent from the
  middleware stack and lists all unprotected routes.
- The scheduled monitor runs every 6 hours and emits a Scout critical alert within 1
  minute of detecting a new critical finding.
- The nightly live checks run at 02:00 UTC without impacting production traffic
  (uses isolated test data, cleaned up after each run).
- The admin dashboard shows the last 30 audit runs with pass/fail status and finding
  counts. Clicking a run shows the detailed findings.
- `GrantHygieneEnforcer` rejects a CrossProductGrant with no expiry unless
  `admin_override` is provided. The override reason is logged to the audit report.
- The isolation audit system itself does not require IsolationMiddleware to run --
  the verifier runs with elevated access (a privileged internal service token) so it
  can read across namespaces to detect leaks.
