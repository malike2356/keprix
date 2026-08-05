"""CLI handlers for ``keprix upstream``."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from keprix.upstream.hermes_adoption import AdoptionPromptGenerator
from keprix.upstream.hermes_monitor import AdoptionStatus, HermesMonitor
from keprix.upstream.inventory_store import refresh_keprix_features
from keprix.upstream.work_package import build_work_package


_STATUS_LABEL = {
    AdoptionStatus.ALREADY_HAVE: "HAVE",
    AdoptionStatus.ADOPT: "ADOPT",
    AdoptionStatus.ADOPT_WITH_HARDENING: "HARDEN",
    AdoptionStatus.SKIP: "SKIP",
    AdoptionStatus.UNEVALUATED: "REVIEW",
    AdoptionStatus.DEFER: "DEFER",
    AdoptionStatus.BLOCKED: "BLOCKED",
}

CRON_LINE = '0 6 * * * keprix upstream check >> /var/log/keprix-upstream.log 2>&1'


def _monitor(args) -> HermesMonitor:
    inventory = getattr(args, "inventory", None)
    return HermesMonitor(inventory_path=inventory)


def cmd_upstream(args) -> int:
    command = args.upstream_command
    handlers = {
        "check": _cmd_check,
        "list": _cmd_list,
        "review": _cmd_review,
        "decide": _cmd_decide,
        "adopt": _cmd_adopt,
        "complete": _cmd_complete,
        "work-package": _cmd_work_package,
        "diff": _cmd_diff,
        "report": _cmd_report,
        "cron-install": _cmd_cron_install,
        "sync-registry": _cmd_sync_registry,
    }
    handler = handlers.get(command)
    if handler is None:
        print(json.dumps({"error": f"unknown upstream command: {command}"}))
        return 2
    return handler(args)


def _cmd_check(args) -> int:
    monitor = _monitor(args)
    features = asyncio.run(
        monitor.check(fetch_enrichment=not getattr(args, "no_enrichment", False))
    )
    if args.json:
        print(monitor.to_json(features))
        return 0
    if not features:
        print("OK: Keprix is current. No new Hermes features to review.")
        print(f"Inventory: {monitor.inventory_path}")
        return 0

    print(f"\nFound {len(features)} new feature(s) from Hermes upstream:\n")
    for feature in features:
        suggested = feature.suggested_status or feature.adoption_status
        label = _STATUS_LABEL.get(feature.adoption_status, "REVIEW")
        print(f"  [{label}] [{feature.category.value}] {feature.name}")
        print(f"     id: {feature.feature_id}")
        print(f"     status: {feature.adoption_status.value}")
        print(f"     suggested: {suggested.value}")
        print(f"     version: {feature.version_introduced}")
        if feature.security_implications:
            print(f"     security: {'; '.join(feature.security_implications)}")
        print()
    print("Run `keprix upstream review` then `keprix upstream decide <id> --status ...`.")
    print("After approval: `keprix upstream adopt <id>`.")
    return 0


def _cmd_list(args) -> int:
    monitor = _monitor(args)
    features = monitor.list_features(
        category=args.category,
        status=args.status,
        pending_only=bool(getattr(args, "pending", False)),
    )
    if args.json:
        print(json.dumps([feature.to_dict() for feature in features], indent=2))
        return 0
    if not features:
        print("No tracked upstream features.")
        return 0
    print(f"Tracked features ({len(features)}):\n")
    for feature in features:
        label = _STATUS_LABEL.get(feature.adoption_status, "REVIEW")
        print(f"  [{label}] {feature.feature_id}")
        print(f"     {feature.name}")
        print(f"     version={feature.version_introduced} status={feature.adoption_status.value}")
        if feature.suggested_status:
            print(f"     suggested={feature.suggested_status.value}")
        if feature.adoption_prompt_id:
            print(f"     prompt={feature.adoption_prompt_id}")
        if feature.work_package_path:
            print(f"     work_package={feature.work_package_path}")
        print()
    return 0


def _cmd_review(args) -> int:
    monitor = _monitor(args)
    features = monitor.list_features(pending_only=True)
    if args.json:
        print(json.dumps([feature.to_dict() for feature in features], indent=2))
        return 0
    if not features:
        print("No features pending review.")
        return 0
    print(f"Pending review ({len(features)}):\n")
    for feature in features:
        suggested = feature.suggested_status.value if feature.suggested_status else "unevaluated"
        print(f"  {feature.feature_id}")
        print(f"     {feature.name}")
        print(f"     category={feature.category.value} suggested={suggested}")
        if feature.triage_notes:
            print(f"     triage: {feature.triage_notes}")
        print(
            f"     decide: keprix upstream decide {feature.feature_id} "
            f"--status adopt_with_hardening"
        )
        print()
    return 0


def _cmd_decide(args) -> int:
    monitor = _monitor(args)
    try:
        feature = monitor.decide(
            args.feature_id,
            args.status,
            decided_by=args.by,
            notes=args.notes or "",
            keprix_equivalent=getattr(args, "equivalent", None),
        )
    except (KeyError, ValueError) as exc:
        print(str(exc))
        return 1
    print(
        f"Decided {feature.feature_id}: {feature.adoption_status.value} "
        f"(by {feature.decided_by})"
    )
    if feature.adoption_status.value in {"adopt", "adopt_with_hardening"}:
        print(f"Next: keprix upstream adopt {feature.feature_id}")
    return 0


def _cmd_adopt(args) -> int:
    monitor = _monitor(args)
    generator = AdoptionPromptGenerator(
        monitor,
        prompts_dir=getattr(args, "prompts_dir", None),
        work_packages_dir=getattr(args, "work_packages_dir", None),
    )
    try:
        output_path = generator.generate(args.feature_id)
    except KeyError as exc:
        print(str(exc))
        return 1
    except PermissionError as exc:
        print(str(exc))
        return 1
    feature = monitor.get_feature(args.feature_id)
    print(f"Generated adoption prompt: {output_path}")
    if feature and feature.work_package_path:
        print(f"Work package: {feature.work_package_path}")
    return 0


def _cmd_complete(args) -> int:
    monitor = _monitor(args)
    try:
        feature = monitor.mark_complete(
            args.feature_id,
            keprix_equivalent=args.equivalent,
            notes=args.notes or "",
            decided_by=args.by,
        )
    except KeyError as exc:
        print(str(exc))
        return 1
    print(
        f"Completed {feature.feature_id}: already_have via {feature.keprix_equivalent}"
    )
    print("Reminder: run parity gates before shipping.")
    print("  bash scripts/check-tui-parity.sh")
    print("  bash scripts/check-tui-surpass-hermes.sh")
    print("  bash scripts/check-agent-parity.sh")
    return 0


def _cmd_work_package(args) -> int:
    monitor = _monitor(args)
    feature = monitor.get_feature(args.feature_id)
    if feature is None:
        print(f"Unknown upstream feature: {args.feature_id}")
        return 1
    if args.regenerate:
        try:
            path = build_work_package(
                feature,
                prompt_path=feature.adoption_prompt_id,
                output_dir=getattr(args, "work_packages_dir", None),
            )
        except ValueError as exc:
            print(str(exc))
            return 1
        feature.work_package_path = str(path)
        monitor._persist_feature(feature)
        print(f"Wrote work package: {path}")
        return 0
    path = feature.work_package_path
    if not path or not Path(path).exists():
        print("No work package on file. Approve, run adopt, or use --regenerate.")
        return 1
    print(Path(path).read_text(encoding="utf-8"))
    return 0


def _cmd_diff(args) -> int:
    monitor = _monitor(args)
    payload = monitor.feature_diff()
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print("Keprix vs Hermes feature diff")
    print(f"  Inventory: {payload.get('inventory_path')}")
    print(f"  Keprix capabilities in inventory: {payload['keprix_prompt_count']}")
    print(f"  Tracked Hermes features: {payload['tracked_hermes_features']}")
    print(f"  Pending review: {payload.get('pending_review', 0)}")
    print(f"  Approved for adopt: {payload['adoptable_features']}")
    print(f"  Processed Hermes versions: {', '.join(payload['processed_versions']) or 'none'}")
    print(f"  PyPI latest: {payload.get('pypi_last_version') or 'unknown'}")
    print(f"  Keprix version: {payload['keprix_version']}")
    return 0


def _cmd_report(args) -> int:
    monitor = _monitor(args)
    payload = monitor.report()
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print("=" * 60)
    print("KEPRIX UPSTREAM ADOPTION REPORT")
    print(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)
    print(f"\n  Inventory: {payload.get('inventory_path')}")
    print(f"  Hermes versions tracked: {payload['processed_versions']}")
    print(f"  Keprix inventory capabilities: {payload['keprix_features']}")
    print(f"  Tracked Hermes features: {payload['tracked_features']}")
    print(f"  Pending review: {payload.get('pending_review', 0)}")
    print(f"  Next prompt number: {payload['next_prompt_number']}")
    print(f"  Last check: {payload.get('last_check') or 'never'}")
    if payload["by_status"]:
        print("\n  By adoption status:")
        for key, count in sorted(payload["by_status"].items()):
            print(f"    {key}: {count}")
    if payload["by_category"]:
        print("\n  By category:")
        for key, count in sorted(payload["by_category"].items()):
            print(f"    {key}: {count}")
    return 0


def _cmd_cron_install(args) -> int:
    print("Daily upstream check (6:00 UTC):")
    print(CRON_LINE)
    print()
    print("Optional Hermes-style cron job:")
    print(
        "keprix cron create --name keprix-upstream-check --schedule \"0 6 * * *\" "
        "--prompt \"Run keprix upstream check and summarize adoptable Hermes features.\" "
        "--enabled-toolsets terminal,file"
    )
    if not getattr(args, "install", False):
        print()
        print("Re-run with --install to append the system crontab line if missing.")
        return 0

    if shutil.which("crontab") is None:
        print("crontab not available on this host; print-only mode.")
        return 1

    try:
        current = subprocess.run(
            ["crontab", "-l"],
            check=False,
            capture_output=True,
            text=True,
        )
        existing = current.stdout if current.returncode == 0 else ""
        if "keprix upstream check" in existing:
            print("Crontab already contains keprix upstream check.")
            return 0
        merged = existing.rstrip() + ("\n" if existing.strip() else "") + CRON_LINE + "\n"
        proc = subprocess.run(
            ["crontab", "-"],
            input=merged,
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(proc.stderr or "Failed to install crontab entry.")
            return 1
        # Ensure log path parent exists when possible
        log_parent = Path("/var/log")
        if log_parent.exists() and os.access(log_parent, os.W_OK):
            Path("/var/log/keprix-upstream.log").touch(exist_ok=True)
        print("Installed daily crontab entry for keprix upstream check.")
        return 0
    except Exception as exc:
        print(f"Could not install crontab: {exc}")
        return 1


def _cmd_sync_registry(args) -> int:
    monitor = _monitor(args)
    caps = refresh_keprix_features(monitor.inventory_path)
    monitor.inventory = monitor._load_inventory()
    print(f"Synced {len(caps)} capabilities into {monitor.inventory_path}")
    return 0
