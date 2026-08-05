"""CLI handlers for ``keprix upgrade``."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from keprix.upgrade.changelog import entries_between, load_changelog
from keprix.upgrade.check import check_upgrade
from keprix.upgrade.context import UpgradeContext
from keprix.upgrade.dry_run import DryRunOptions, dry_run_upgrade
from keprix.upgrade.execute import ExecuteOptions, UpgradeExecutor, rollback_last_upgrade
from keprix.upgrade.history import load_history
from keprix.upgrade.plan import build_upgrade_plan
from keprix.upgrade.discovery import FeatureDiscovery
from keprix.upgrade.prompts import apply_adoption_prompt, list_adoption_prompt_details

logger = logging.getLogger(__name__)


def _print_check(result, *, as_json: bool, from_version: str, to_version: str) -> int:
    if as_json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.compatible else 1

    print(f"\nUpgrade Check: {result.product}")
    print(f"   Current Keprix: {result.current_version}")
    print(f"   Target Keprix:  {result.target_version}")
    print(f"   Risk:           {result.risk.upper()}")
    print("-" * 60)
    print(f"Breaking Changes ({len(result.breaking_changes)})")
    if result.breaking_changes:
        for entry in result.breaking_changes:
            print(f"  - {entry.get('title', entry.get('id', 'breaking'))}")
    else:
        print("  None.")
    print(f"\nDeprecations ({len(result.deprecated_features)})")
    if result.deprecated_features:
        for entry in result.deprecated_features:
            print(f"  - {entry.get('title', entry.get('id', 'deprecation'))}")
    else:
        print("  None.")
    print(f"\nNew Features ({len(result.new_features)})")
    for entry in result.new_features[:10]:
        version = entry.get("version", "")
        title = entry.get("title", entry.get("id", "feature"))
        suffix = f" ({version})" if version else ""
        print(f"  - {title}{suffix}")
    if len(result.new_features) > 10:
        print(f"  ... and {len(result.new_features) - 10} more")
    print(f"\nConfig Migrations ({len(result.config_migrations_required)})")
    for entry in result.config_migrations_required:
        print(f"  - {entry.get('title', entry.get('id', 'migration'))}")

    discovery = FeatureDiscovery()
    new_features = discovery.get_new_features(from_version, to_version)
    if new_features:
        print(f"\nKeprix Modules ({len(new_features)})")
        for feature in new_features:
            tag = "requires config" if feature.requires_config else "opt-in"
            if feature.breaking:
                tag = "BREAKING"
            print(f"  - {feature.name}: {feature.description} [{tag}]")
            if feature.migration_guide:
                print(f"      guide: {feature.migration_guide}")
            if feature.prompt_name:
                print(f"      adopt: keprix upgrade --prompt {feature.prompt_name}")

    breaking = discovery.get_breaking_changes(from_version, to_version)
    if breaking and not result.breaking_changes:
        print(f"\nBreaking Module Changes ({len(breaking)})")
        for feature in breaking:
            print(f"  - {feature.name}: {feature.description}")
            if feature.migration_guide:
                print(f"      guide: {feature.migration_guide}")

    print("-" * 60)
    print(f"Recommendation: {result.recommendation}")
    if result.changelog_url:
        print(f"Changelog: {result.changelog_url}")
    if result.compatible and result.risk in {"none", "low"}:
        print(f"\nNext: keprix upgrade --dry-run --to {result.target_version}")
    return 0


def _print_list_prompts(*, as_json: bool) -> int:
    prompts = list_adoption_prompt_details()
    if as_json:
        print(
            json.dumps(
                [
                    {
                        "name": p.name,
                        "version": p.version,
                        "title": p.title,
                        "description": p.description,
                        "feature_key": p.feature_key,
                    }
                    for p in prompts
                ],
                indent=2,
            )
        )
        return 0
    print("\nAvailable upgrade prompts:")
    for prompt in prompts:
        version = f" ({prompt.version})" if prompt.version else ""
        print(f"  {prompt.name}{version}")
        print(f"    {prompt.title}: {prompt.description}")
    print("\nRun: keprix upgrade --prompt <name>")
    return 0


def _resolve_upgrade_action(args) -> str | None:
    flags = [
        ("check", bool(getattr(args, "check", False))),
        ("plan", bool(getattr(args, "plan", False))),
        ("list", bool(getattr(args, "list", False))),
        ("list-prompts", bool(getattr(args, "list_prompts", False))),
        ("dry-run", bool(getattr(args, "dry_run", False))),
        ("rollback", bool(getattr(args, "rollback", False))),
        ("prompt", bool(getattr(args, "prompt_name", None))),
        (
            "execute",
            bool(getattr(args, "to", None))
            and not any(
                [
                    getattr(args, "check", False),
                    getattr(args, "plan", False),
                    getattr(args, "dry_run", False),
                ]
            ),
        ),
    ]
    selected = [name for name, on in flags if on]
    if len(selected) > 1:
        raise ValueError(
            "Specify one upgrade action: --check, --plan, --list, --list-prompts, "
            "--dry-run, --rollback, --prompt, or --to <version>."
        )
    return selected[0] if selected else None


def _print_plan(plan, product_name: str, *, detailed: bool) -> int:
    print(f"\nUpgrade Path: {product_name} on Keprix {plan.from_version} -> {plan.to_version}")
    if not plan.steps:
        print("   No intermediate steps. Already on target or no releases in range.")
        return 0
    for index, step in enumerate(plan.steps, start=1):
        print(f"\nStep {index}: {step.from_version} -> {step.to_version}")
        for feature in step.features:
            print(f"   + {feature.get('title', feature.get('id', 'feature'))}")
        for migration in step.config_migrations:
            print(f"   ~ {migration.get('title', migration.get('id', 'migration'))}")
        if detailed and step.migration_steps:
            for migration in step.migration_steps:
                print(f"   > migration: {migration.name} ({migration.description})")
        print(f"   Risk: {step.risk.upper()}")
        print(f"   {len(step.breaking_changes)} breaking change(s)")
    if plan.direct_jump_recommended and plan.step_count > 1:
        print(f"\nDirect jump: {plan.from_version} -> {plan.to_version} (recommended)")
        print("   Intermediate migrations are cumulative.")
    return 0


def _print_history(records, product_name: str, current_version: str) -> int:
    print(f"\n{product_name} Upgrade History")
    print("-" * 60)
    if not records:
        print("   No upgrades recorded yet.")
        print(f"   Current: {current_version}")
        return 0
    print(f"{'#':<3} {'From':<8} {'To':<8} {'Date':<20} {'Status':<12} {'Duration'}")
    print("-" * 60)
    for index, record in enumerate(records, start=1):
        date = record.timestamp[:19].replace("T", " ")
        duration = f"{record.duration_seconds:.1f}s" if record.duration_seconds else "-"
        print(
            f"{index:<3} {record.from_version:<8} {record.to_version:<8} "
            f"{date:<20} {record.status:<12} {duration}"
        )
    print("-" * 60)
    print(f"Current: {current_version}")
    print("Backups preserved in .keprix/upgrade/backups/")
    return 0


def _print_dry_run(result) -> int:
    print(f"\nDry Run: {result.product} -> Keprix {result.target_version}")
    print(f"   Duration: {result.duration_seconds:.1f}s")
    if result.total_tests:
        status = "PASSED" if result.passed else "FAILED"
        print(f"   {status}: {result.passed_tests}/{result.total_tests}")
    if result.warnings:
        print(f"   Warnings: {len(result.warnings)}")
        for warning in result.warnings[:5]:
            print(f"      - {warning}")
    if result.failed_test_details:
        print("   Failed tests:")
        for detail in result.failed_test_details[:10]:
            print(f"      x {detail}")
    print(f"\nRecommendation: {result.recommendation}")
    return 0 if result.passed else 1


def cmd_upgrade(args) -> int:
    """Dispatch ``keprix upgrade`` subcommands."""
    try:
        action = _resolve_upgrade_action(args)
    except ValueError as exc:
        print(str(exc))
        return 2

    if action is None:
        print("Specify an upgrade action. Try: keprix upgrade --help")
        return 2

    as_json = bool(getattr(args, "json", False))

    if action == "list-prompts":
        return _print_list_prompts(as_json=as_json)

    try:
        ctx = UpgradeContext.resolve(
            Path(args.path) if getattr(args, "path", None) else None
        )
    except FileNotFoundError as exc:
        print(str(exc))
        return 2

    if action == "check":
        target = ctx.resolve_target(getattr(args, "to", None))
        releases = load_changelog(ctx.changelog_path)
        changelog = entries_between(ctx.installed_version, target, releases)
        result = check_upgrade(
            ctx.manifest.to_upgrade_info(),
            ctx.installed_version,
            target,
            ctx.available_versions,
            changelog=changelog,
            changelog_url=f"https://github.com/malike2356/keprix/releases/tag/v{target}",
        )
        return _print_check(
            result,
            as_json=as_json,
            from_version=ctx.installed_version,
            to_version=target,
        )

    if action == "plan":
        target = ctx.resolve_target(getattr(args, "to", None))
        releases = load_changelog(ctx.changelog_path)
        plan = build_upgrade_plan(
            ctx.installed_version,
            target,
            ctx.available_versions,
            releases=releases,
        )
        return _print_plan(
            plan,
            ctx.manifest.product_name,
            detailed=bool(getattr(args, "step", False)),
        )

    if action == "list":
        history_path = ctx.product_path / ".keprix" / "upgrade" / "history.json"
        records = load_history(history_path)
        return _print_history(records, ctx.manifest.product_name, ctx.installed_version)

    if action == "dry-run":
        if not getattr(args, "to", None):
            print("--dry-run requires --to <version>.")
            return 2
        target = ctx.resolve_target(getattr(args, "to", None))
        result = dry_run_upgrade(
            ctx.manifest.product_name,
            target,
            ctx.product_path,
            options=DryRunOptions(skip_tests=bool(getattr(args, "skip_tests", False))),
        )
        return _print_dry_run(result)

    if action == "execute":
        if not getattr(args, "to", None):
            print("--to <version> is required to execute an upgrade.")
            return 2
        target = ctx.resolve_target(getattr(args, "to", None))
        executor = UpgradeExecutor(
            manifest=ctx.manifest,
            product_path=ctx.product_path,
            target_version=target,
            installed_version=ctx.installed_version,
            options=ExecuteOptions(
                skip_confirmation=bool(getattr(args, "force", False)),
                force=bool(getattr(args, "force", False)),
            ),
        )
        ok = executor.execute()
        if ok:
            print(
                f"\nDone: {ctx.manifest.product_name} upgraded to Keprix {target}."
            )
            print("Review new features with `keprix upgrade --plan`.")
            return 0
        print("\nUpgrade failed.")
        return 1

    if action == "rollback":
        ok = rollback_last_upgrade(
            ctx.product_path,
            options=ExecuteOptions(
                skip_confirmation=bool(getattr(args, "force", False)),
                force=bool(getattr(args, "force", False)),
            ),
        )
        if ok:
            print("\nRollback complete. Backup preserved.")
            return 0
        print("\nRollback failed.")
        return 1

    if action == "prompt":
        prompt_name = getattr(args, "prompt_name", "")
        try:
            result = apply_adoption_prompt(
                prompt_name,
                ctx.product_path,
                assume_yes=bool(getattr(args, "yes", False)),
            )
        except (ValueError, FileNotFoundError) as exc:
            print(str(exc))
            return 2
        if as_json:
            print(json.dumps(result, indent=2))
            return 0 if result.get("applied") else 1
        if result.get("applied"):
            print(f"\nDone: applied {prompt_name}.")
            if result.get("config_written"):
                print(f"   Config created: {result['config_written']}")
            return 0
        print(f"\nNot applied: {result.get('reason', 'unknown')}.")
        return 1

    print("Specify an upgrade action. Try: keprix upgrade --help")
    return 2
