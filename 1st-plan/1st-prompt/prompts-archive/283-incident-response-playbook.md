# Prompt 93; Incident Response Playbook & Security Operations Runbook

## 0. What This Completes

Prompts 87-92 built the defenses. Prompt 93 is what you do when defenses are breached; the incident response playbook, security operations procedures, and the runbook that keeps the entire Keprix-Scout-Carina ecosystem secure day-to-day.

## 1. Incident Severity Levels

| Level | Name | Trigger | Response Time | Auto-Response |
|-------|------|---------|---------------|---------------|
| **L1** | INFO | Anomalous but not threatening. Rate limit hit, unusual tool usage. | Review within 24h | Log only |
| **L2** | WARNING | Suspicious pattern. Multiple blocked injections, repeated egress attempts. | Investigate within 4h | Quarantine tool |
| **L3** | CRITICAL | Active threat. Credential access attempt, coordinated injection campaign, sandbox escape attempt. | Respond within 15min | Block session + alert operator |
| **L4** | EMERGENCY | Breach in progress. Credential leaked, data exfiltration confirmed, lateral movement detected. | Respond IMMEDIATELY | Full instance suspension + credential rotation |

## 2. Incident Response Procedures

### 2.1 L3 CRITICAL; Active Threat

```
TRIGGER: Scout RASP detects 3+ critical signals from same session in 10 minutes.

IMMEDIATE (0-5 minutes):
  1. Scout auto-response: BLOCK_SESSION sent to Keprix
  2. Operator receives Slack + email alert
  3. Forensic snapshot automatically captured

INVESTIGATE (5-30 minutes):
  4. Operator opens Scout dashboard → correlation view
  5. Check: is this a false positive? (Carina AI analysis)
  6. Check: any other products affected? (cross-product correlation)
  7. Check: what's the blast radius? (session only or instance-wide?)
  8. Check: any credential access? (vault audit log)

CONTAIN (30-60 minutes):
  9. If credential access suspected → rotate all credentials
  10. If lateral movement suspected → suspend all sessions from same IP
  11. If tool abuse confirmed → quarantine abused tool
  12. Collect forensic evidence for post-mortem

RECOVER (1-4 hours):
  13. Review and update security policies if gap found
  14. Add attack pattern to injection catalog
  15. Deploy policy update to all affected products
  16. Monitor for 24h before clearing incident

POST-MORTEM (24-72 hours):
  17. Root cause analysis document
  18. Update pentest checklist with new attack vector
  19. Add regression test for the specific attack
  20. Update this playbook if procedures were insufficient
```

### 2.2 L4 EMERGENCY; Breach in Progress

```
TRIGGER: Credential exfiltration confirmed, data leak detected, or lateral movement across products.

IMMEDIATE (0-2 minutes):
  1. Scout auto-response: SUSPEND sent to Keprix (instance-wide)
  2. If auto-response disabled: operator hits EMERGENCY SUSPEND in Scout dashboard
  3. ALL sessions terminated immediately
  4. ALL network egress blocked
  5. Forensic snapshot captured
  6. Credential vault sealed (no new token issuance)
  7. Operator paged via ALL channels (Slack + email + SMS + push)

CONTAIN (2-15 minutes):
  8. Identify attack vector: which tool? which session? which credential?
  9. Check Scout correlation: any other products compromised?
  10. Rotate ALL credentials; API keys, Stripe, provider tokens
  11. Revoke ALL active agent tokens
  12. Block attacker IP/subnet across ALL products via Scout

INVESTIGATE (15-60 minutes):
  13. Pull full audit trail for compromised session(s)
  14. Carina AI analysis: reconstruct attack chain
  15. Determine: what data was accessed? what was exfiltrated?
  16. If PII/customer data exposed → legal team notified
  17. If financial data exposed → Stripe notified, fraud monitoring activated

RECOVER (1-8 hours):
  18. Restore from last clean checkpoint
  19. Deploy security patch if vulnerability found
  20. Gradual re-enable: governance → sandbox → tools → network → A2A
  21. Monitor for 48h before declaring all-clear

POST-MORTEM (24-72 hours):
  22. Full incident report with timeline
  23. Root cause analysis
  24. Customer notification if data breach (GDPR: within 72h)
  25. Regulatory notification if required
  26. Update all security policies
  27. Add regression tests for attack vector
  28. Board/leadership briefing
```

---

## 3. Security Operations Runbook

### 3.1 Daily Operations

```bash
# Morning checklist (automated via cron)
keprix ops daily-check
```

| Time | Task | Command | Expected |
|------|------|---------|----------|
| 06:00 | Upstream monitor | `keprix upstream check` | Report: new Hermes features |
| 06:30 | Scout heartbeat verify | `keprix scout ping` | All products online |
| 07:00 | Credential expiry check | `keprix vault audit --expiring 7d` | No expiring credentials |
| 07:30 | Daily security digest | `keprix ops report --24h` | Signal counts, blocked attempts |
| 08:00 | Policy compliance check | `keprix ops compliance` | All products in policy |

### 3.2 Weekly Operations

| Day | Task | Command | Expected |
|-----|------|---------|----------|
| Monday | Scout correlation review | Manual: Scout dashboard → correlation | Any cross-product patterns? |
| Monday | Policy review | `keprix ops policy-review` | Any policies need updating? |
| Tuesday | Credential rotation check | `keprix vault audit --rotation-due` | Rotate credentials due this week |
| Wednesday | Pentest run | `keprix security pentest --quick` | All baseline tests pass |
| Thursday | Audit chain verification | `keprix audit verify` | Chain intact, no tampering |
| Friday | Weekly ops report | `keprix ops report --weekly` | Summary for leadership |
| Friday | Carina AI recommendations | Manual: Scout → Carina recommendations | Apply suggested improvements |

### 3.3 Monthly Operations

| Task | Command | Expected |
|------|---------|----------|
| Full pentest suite | `keprix security pentest --full` | All 37 tests pass |
| Compliance evidence sync | `keprix ops compliance-sync --full` | All frameworks updated |
| Dependency audit | `keprix security audit --full` | No critical CVEs |
| Policy effectiveness review | Manual: review blocked vs allowed ratio | Tune thresholds if too aggressive |
| Capacity planning | `keprix ops capacity` | Storage, Redis, API quota headroom |
| Incident response drill | Manual: simulate L3 incident | Response time under 15min |
| Scout-Carina health check | `keprix scout integration-test` | End-to-end passes |

---

## 4. Automated Runbook

```python
# keprix/ops/runbook.py

"""
Automated security operations runbook.

Daily, weekly, and monthly tasks automated via cron.
Results pushed to Scout dashboard and operator's preferred channels.
"""

import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List


@dataclass
class OpsCheck:
    name: str
    command: str
    expected: str
    result: str = "pending"
    passed: bool = False
    details: str = ""


class RunbookExecutor:
    """Executes runbook tasks and reports results."""

    async def daily(self) -> List[OpsCheck]:
        """Execute daily runbook."""
        checks = []

        # 1. Upstream monitor
        checks.append(await self._run("Upstream monitor", "keprix upstream check"))

        # 2. Scout heartbeat
        checks.append(await self._run("Scout heartbeat", "keprix scout ping"))

        # 3. Credential expiry
        checks.append(await self._run("Credential expiry", "keprix vault audit --expiring 7d"))

        # 4. Signal summary
        checks.append(await self._run("Signal summary", "keprix ops report --24h"))

        # 5. Check for failed checks
        failures = [c for c in checks if not c.passed]
        if failures:
            await self._alert("Daily runbook failures", failures)

        return checks

    async def weekly(self) -> List[OpsCheck]:
        """Execute weekly runbook."""
        checks = []

        checks.append(await self._run("Policy review", "keprix ops policy-review"))
        checks.append(await self._run("Credential rotation", "keprix vault audit --rotation-due"))
        checks.append(await self._run("Quick pentest", "keprix security pentest --quick"))
        checks.append(await self._run("Audit chain", "keprix audit verify"))
        checks.append(await self._run("Weekly report", "keprix ops report --weekly"))

        # Carina AI recommendations (manual review required)
        checks.append(OpsCheck(
            name="Carina AI recommendations",
            command="Manual: Scout → Carina → Recommendations",
            expected="Review and apply suggested improvements",
            result="requires_manual_review",
        ))

        return checks

    async def monthly(self) -> List[OpsCheck]:
        """Execute monthly runbook."""
        checks = []

        checks.append(await self._run("Full pentest", "keprix security pentest --full"))
        checks.append(await self._run("Compliance sync", "keprix ops compliance-sync --full"))
        checks.append(await self._run("Dependency audit", "keprix security audit --full"))
        checks.append(await self._run("Capacity check", "keprix ops capacity"))
        checks.append(await self._run("Scout integration test", "keprix scout integration-test"))

        checks.append(OpsCheck(
            name="Incident response drill",
            command="Manual: simulate L3 incident",
            expected="Response time < 15 minutes",
            result="requires_manual_execution",
        ))

        return checks

    async def _run(self, name: str, command: str) -> OpsCheck:
        """Run a single check and return result."""
        try:
            result = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()

            return OpsCheck(
                name=name,
                command=command,
                expected="Success",
                result="passed" if result.returncode == 0 else "failed",
                passed=result.returncode == 0,
                details=stdout.decode()[:500] if stdout else stderr.decode()[:500],
            )
        except Exception as e:
            return OpsCheck(
                name=name,
                command=command,
                expected="Success",
                result="error",
                passed=False,
                details=str(e),
            )

    async def _alert(self, title: str, failures: List[OpsCheck]):
        """Alert operator about runbook failures."""
        from keprix.security.scout_client import scout_client, SignalCategory, SignalSeverity

        for f in failures:
            scout_client.send(
                category=SignalCategory.GOVERNANCE,
                severity=SignalSeverity.WARNING,
                action="runbook_check_failed",
                target=f"runbook:{f.name}",
                details={"command": f.command, "error": f.details},
            )
```

---

## 5. Cron Job Registration

```bash
# Daily runbook; 7 AM UTC
keprix cron create \
  --name "keprix-ops-daily" \
  --schedule "0 7 * * *" \
  --prompt "Run the Keprix daily security operations runbook. Execute: upstream check, Scout heartbeat, credential expiry check, 24h signal summary. Report any failures to the operator." \
  --deliver telegram:7028923891 \
  --enabled-toolsets terminal

# Weekly runbook; Monday 8 AM UTC  
keprix cron create \
  --name "keprix-ops-weekly" \
  --schedule "0 8 * * 1" \
  --prompt "Run the Keprix weekly security operations runbook. Execute: policy review, credential rotation check, quick pentest, audit chain verification, weekly report. Flag any policies needing updates. Report Carina AI recommendations." \
  --deliver telegram:7028923891 \
  --enabled-toolsets terminal

# Monthly runbook; 1st of month 9 AM UTC
keprix cron create \
  --name "keprix-ops-monthly" \
  --schedule "0 9 1 * *" \
  --prompt "Run the Keprix monthly security operations runbook. Execute: full pentest suite, compliance evidence sync, dependency audit, capacity check, Scout integration test. Flag: CVEs, policy gaps, capacity warnings, failed integration tests. Schedule incident response drill." \
  --deliver telegram:7028923891 \
  --enabled-toolsets terminal
```

---

## 6. Operator Commands Cheat Sheet

```bash
# ── Scout Commands ─────────────────────────────────
keprix scout ping                     # Check Scout connectivity
keprix scout signals --product abbis --24h  # View recent signals
keprix scout suspend --product petraclus --session 7f3a  # Suspend session
keprix scout quarantine --tool shell-exec --product fleet_z  # Quarantine tool
keprix scout block-egress --product abbis  # Block all egress
keprix scout set-sandbox --mode docker --product petraclus  # Change sandbox

# ── Incident Response ──────────────────────────────
keprix incident declare --level critical --reason "injection_campaign"
keprix incident snapshot --session 7f3a       # Forensic snapshot
keprix incident rotate-creds --product all    # Rotate all credentials
keprix incident seal-vault                    # Seal credential vault
keprix incident lockdown --product petraclus  # Full instance lockdown

# ── Operations ────────────────────────────────────
keprix ops daily-check                        # Run daily runbook
keprix ops report --24h                       # 24h security report
keprix ops report --weekly                    # Weekly summary
keprix ops compliance                         # Compliance status
keprix ops policy-review                      # Policy effectiveness review
keprix ops capacity                           # Capacity headroom
keprix ops drill --level l3                   # Run incident response drill

# ── Forensics ─────────────────────────────────────
keprix forensics snapshot --session 7f3a      # Capture snapshot
keprix forensics list                         # List snapshots
keprix forensics analyze --snapshot ckpt-abc  # Analyse with Carina AI
keprix forensics export --snapshot ckpt-abc   # Export for legal
keprix forensics chain-verify                 # Verify chain of custody
```

---

## 7. Acceptance Criteria

- [ ] L1-L4 incident response procedures documented and tested
- [ ] Daily runbook executes automatically via cron
- [ ] Weekly runbook includes Carina AI recommendation review
- [ ] Monthly runbook includes full pentest + compliance sync
- [ ] Incident response drill completes in under 15 minutes
- [ ] All operator commands work from cheat sheet
- [ ] Runbook failures generate Scout alerts
- [ ] Forensic snapshot capture works on demand
- [ ] Credential rotation procedure tested and documented
- [ ] Post-mortem template ready for incident reports
