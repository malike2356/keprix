"""CLI handlers for self-configuration commands."""

from __future__ import annotations

import asyncio
import getpass
import sys


def cmd_configure(_args) -> int:
    from keprix.config.env_discovery import run_discover_environment

    return run_discover_environment()


def cmd_health(_args) -> int:
    from keprix.config.health_monitor import ConfigHealthMonitor

    monitor = ConfigHealthMonitor()
    asyncio.run(monitor._run_all_checks())
    results = monitor.get_all()
    if not results:
        print("No health data yet. Run checks completed with no configured components.")
        return 0

    print(f"{'Component':<35} {'Status':<12} {'Latency':>10}")
    print("-" * 60)
    for name, health in sorted(results.items()):
        latency = f"{health.latency_ms:.0f}ms" if health.latency_ms > 0 else "-"
        print(f"{name:<35} {health.status:<12} {latency:>10}")
        if health.error:
            print(f"  Error: {health.error[:80]}")
    return 0


def cmd_proposals(_args) -> int:
    from keprix.config.optimizer import _load_pending_proposals

    pending = _load_pending_proposals()
    if not pending:
        print("No pending proposals.")
        return 0
    for proposal in pending:
        print(f"[{proposal['proposal_id']}] {proposal['risk'].upper()} - {proposal['category']}")
        print(f"  {proposal['description']}")
        print(f"  Current: {proposal['current_value']}  ->  Proposed: {proposal['proposed_value']}")
        print(f"  Rationale: {proposal['rationale']}")
        print(f"  Env var: {proposal['env_key']}")
        print("")
    return 0


def cmd_approve(args) -> int:
    from keprix.config.optimizer import apply_proposal

    proposal_id = getattr(args, "proposal_id", None)
    if not proposal_id:
        print("Usage: keprix approve <proposal_id>", file=sys.stderr)
        return 2
    approved_by = getpass.getuser()
    success = asyncio.run(apply_proposal(proposal_id, approved_by))
    if success:
        print(f"Applied proposal {proposal_id}. Restart the agent to pick up the change.")
        return 0
    print(f"Proposal {proposal_id} not found.")
    return 1


def cmd_reject(args) -> int:
    from keprix.config.optimizer import reject_proposal

    proposal_id = getattr(args, "proposal_id", None)
    if not proposal_id:
        print("Usage: keprix reject <proposal_id>", file=sys.stderr)
        return 2
    if reject_proposal(proposal_id):
        print(f"Dismissed proposal {proposal_id}.")
        return 0
    print(f"Proposal {proposal_id} not found.")
    return 1


def cmd_repair(_args) -> int:
    from keprix.config.auto_repair import repair_all_components
    from keprix.config.health_monitor import ConfigHealthMonitor

    monitor = ConfigHealthMonitor()
    asyncio.run(repair_all_components(monitor))
    print("Repair pass complete. Run `keprix health` to review component status.")
    return 0


def cmd_rollback(args) -> int:
    from keprix.config.optimizer import rollback_env_var

    env_key = getattr(args, "env_key", None)
    if not env_key:
        print("Usage: keprix rollback <env_key>", file=sys.stderr)
        return 2
    if asyncio.run(rollback_env_var(env_key)):
        print(f"Rolled back {env_key}. Restart the agent to pick up the change.")
        return 0
    print(f"No rollback record found for {env_key}.")
    return 1
