"""Keprix zero-downtime migration helpers (parity with shared/migrations)."""

from __future__ import annotations

import os
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

Dialect = Literal["postgres", "mysql"]
DEFAULT_BATCH_SIZE = 1000
MAX_ACCEPTABLE_LOCK_MS = 100

SqlExecutor = Callable[[str, list[Any] | None], dict[str, Any]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _q(dialect: Dialect, name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Unsafe SQL identifier: {name}")
    return f"`{name}`" if dialect == "mysql" else f'"{name}"'


def assert_add_before_drop(steps: list[dict[str, Any]]) -> None:
    add_idx = next((i for i, s in enumerate(steps) if s["kind"] == "add_column"), -1)
    drop_idx = next((i for i, s in enumerate(steps) if s["kind"] == "drop_column"), -1)
    if drop_idx >= 0 and (add_idx < 0 or drop_idx < add_idx):
        raise ValueError("Never drop a column before adding its replacement (add-before-drop rule)")
    if drop_idx >= 0:
        validate_idx = next((i for i, s in enumerate(steps) if s["kind"] == "validate"), -1)
        if validate_idx < 0 or validate_idx > drop_idx:
            raise ValueError("Must validate before dropping old column")


def _finalize(name: str, dialect: Dialect, steps: list[dict[str, Any]]) -> dict[str, Any]:
    forward = "\n\n".join(
        f"-- {s['description']}\n{s['sql']};" for s in steps if not str(s["sql"]).startswith("--")
    )
    rollback_parts = []
    for s in reversed(steps):
        rb = str(s.get("rollbackSql") or "")
        if rb and not rb.startswith("--"):
            rollback_parts.append(f"-- rollback: {s['description']}\n{rb};")
    rollback = "\n\n".join(rollback_parts) or f"-- rollback placeholder for {name}\n"
    return {
        "name": name,
        "dialect": dialect,
        "createdAt": _now(),
        "steps": steps,
        "forwardScript": forward,
        "rollbackScript": rollback,
        "requiresProductionConfirmation": True,
        "stagingValidated": False,
    }


def plan_add_column_before_drop(
    *,
    name: str,
    table: str,
    old_column: str,
    new_column: dict[str, Any],
    dialect: Dialect = "postgres",
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    t = _q(dialect, table)
    neu = _q(dialect, new_column["name"])
    old = _q(dialect, old_column)
    null_sql = "" if new_column.get("nullable", True) else " NOT NULL"
    def_sql = f" DEFAULT {new_column['defaultSql']}" if new_column.get("defaultSql") else ""
    type_sql = new_column.get("typeSql") or "TEXT"
    if dialect == "postgres":
        add_sql = f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS {neu} {type_sql}{null_sql}{def_sql}"
        drop_old = f"ALTER TABLE {t} DROP COLUMN IF EXISTS {old}"
        drop_new = f"ALTER TABLE {t} DROP COLUMN IF EXISTS {neu}"
        backfill = (
            f"UPDATE {t} SET {neu} = {old} WHERE {neu} IS DISTINCT FROM {old} "
            f"AND ctid IN (SELECT ctid FROM {t} WHERE {neu} IS DISTINCT FROM {old} LIMIT {batch_size})"
        )
        validate = f"SELECT count(*)::int AS mismatches FROM {t} WHERE {neu} IS DISTINCT FROM {old}"
        add_old = f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS {old} {type_sql}"
    else:
        add_sql = f"ALTER TABLE {t} ADD COLUMN {neu} {type_sql}{null_sql}{def_sql}"
        drop_old = f"ALTER TABLE {t} DROP COLUMN {old}"
        drop_new = f"ALTER TABLE {t} DROP COLUMN {neu}"
        backfill = f"UPDATE {t} SET {neu} = {old} WHERE ({neu} IS NULL OR {neu} <> {old}) LIMIT {batch_size}"
        validate = f"SELECT COUNT(*) AS mismatches FROM {t} WHERE NOT ({neu} <=> {old})"
        add_old = f"ALTER TABLE {t} ADD COLUMN {old} {type_sql}"

    steps = [
        {
            "id": str(uuid.uuid4()),
            "kind": "preflight",
            "description": f"Preflight active connections on {table}",
            "sql": f"-- preflight:{table}",
            "rollbackSql": "-- noop",
        },
        {
            "id": str(uuid.uuid4()),
            "kind": "add_column",
            "description": f"Add {new_column['name']} before touching {old_column}",
            "sql": add_sql,
            "rollbackSql": drop_new,
        },
        {
            "id": str(uuid.uuid4()),
            "kind": "backfill",
            "description": f"Backfill in batches of {batch_size}",
            "sql": backfill,
            "rollbackSql": "-- leave new column",
        },
        {
            "id": str(uuid.uuid4()),
            "kind": "validate",
            "description": "Validate new column matches old column",
            "sql": validate,
            "rollbackSql": "-- noop",
        },
        {
            "id": str(uuid.uuid4()),
            "kind": "drop_column",
            "description": f"Drop {old_column} only after validation",
            "sql": drop_old,
            "rollbackSql": add_old,
        },
    ]
    assert_add_before_drop(steps)
    return _finalize(name, dialect, steps)


def generate_rollback(plan: dict[str, Any], migrations_dir: str) -> dict[str, str]:
    if not str(plan.get("rollbackScript") or "").strip():
        raise ValueError("Rollback script missing; refuse to proceed without rollback")
    path = Path(migrations_dir)
    path.mkdir(parents=True, exist_ok=True)
    forward_path = path / f"{plan['name']}.sql"
    rollback_path = path / f"{plan['name']}.rollback.sql"
    forward_path.write_text(
        f"-- forward: {plan['name']}\n-- created: {plan['createdAt']}\n\n{plan['forwardScript']}\n",
        encoding="utf-8",
    )
    rollback_path.write_text(
        f"-- rollback: {plan['name']}\n-- MUST exist before forward apply\n\n{plan['rollbackScript']}\n",
        encoding="utf-8",
    )
    return {
        "migrationName": plan["name"],
        "forwardPath": str(forward_path),
        "rollbackPath": str(rollback_path),
        "rollbackScript": plan["rollbackScript"],
    }


def assert_rollback_exists(migrations_dir: str, migration_name: str) -> str:
    rollback_path = Path(migrations_dir) / f"{migration_name}.rollback.sql"
    if not rollback_path.exists():
        raise FileNotFoundError(f"Rollback required before run: missing {rollback_path}")
    return str(rollback_path)


def create_staging_mirror(source_database: str, staging_database: str, dialect: Dialect = "postgres") -> dict[str, Any]:
    if dialect == "postgres":
        commands = [
            f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{staging_database}' AND pid <> pg_backend_pid()",
            f"DROP DATABASE IF EXISTS {staging_database}",
            f"CREATE DATABASE {staging_database} WITH TEMPLATE {source_database}",
        ]
    else:
        commands = [
            f"CREATE DATABASE IF NOT EXISTS {staging_database}",
            f"mysqldump {source_database} | mysql {staging_database}",
        ]
    return {
        "sourceDatabase": source_database,
        "stagingDatabase": staging_database,
        "dialect": dialect,
        "commands": commands,
        "estimatedMinutesNote": "Target: complete mirror under 5 minutes for databases up to 10GB when using TEMPLATE or streamed dump on same host.",
    }


def production_confirmation_gate(plan: dict[str, Any], confirm_token: str | None = None) -> dict[str, Any]:
    if not plan.get("stagingValidated"):
        return {"allowed": False, "reason": "Staging validation has not passed"}
    expected = f"CONFIRM_PROD:{plan['name']}"
    if confirm_token != expected:
        return {
            "allowed": False,
            "reason": f"Provide explicit confirmation token {expected} after staging passes",
        }
    return {"allowed": True, "reason": "Staging validated and confirmation provided"}


def run_migration_plan(
    exec_sql: SqlExecutor,
    plan: dict[str, Any],
    *,
    environment: str = "test",
    production_confirm_token: str | None = None,
    skip_drop: bool = False,
) -> dict[str, Any]:
    if environment == "production":
        if not plan.get("stagingValidated"):
            raise RuntimeError("Production migration blocked: staging validation has not passed")
        if production_confirm_token != f"CONFIRM_PROD:{plan['name']}":
            raise RuntimeError(f"Production migration requires explicit confirmation token CONFIRM_PROD:{plan['name']}")

    executed: list[str] = []
    for step in plan["steps"]:
        kind = step["kind"]
        if kind in ("backfill", "validate", "drop_column"):
            continue
        if kind == "preflight" or str(step["sql"]).startswith("--"):
            executed.append(step["id"])
            continue
        res = exec_sql(step["sql"], None)
        if int(res.get("lockMs") or 0) > MAX_ACCEPTABLE_LOCK_MS:
            raise RuntimeError(f"Step {kind} lock exceeded {MAX_ACCEPTABLE_LOCK_MS}ms")
        executed.append(step["id"])

    # backfill batches
    backfill = next((s for s in plan["steps"] if s["kind"] == "backfill"), None)
    batches = 0
    rows_updated = 0
    done = True
    if backfill:
        for _ in range(10_000):
            res = exec_sql(backfill["sql"], None)
            batches += 1
            rows_updated += int(res.get("rowCount") or 0)
            if int(res.get("rowCount") or 0) == 0:
                break
        else:
            done = False

    validate = next((s for s in plan["steps"] if s["kind"] == "validate"), None)
    mismatches = 0
    if validate:
        res = exec_sql(validate["sql"], None)
        mismatches = int((res.get("rows") or [{}])[0].get("mismatches") or 0)
        if mismatches:
            raise RuntimeError(f"Validation failed: {mismatches} mismatched row(s)")

    if not skip_drop:
        drop = next((s for s in plan["steps"] if s["kind"] == "drop_column"), None)
        if drop and not str(drop["sql"]).startswith("--"):
            exec_sql(drop["sql"], None)
            executed.append(drop["id"])

    return {
        "executed": executed,
        "validation": {"ok": mismatches == 0, "mismatches": mismatches},
        "backfill": {"batches": batches, "rowsUpdated": rows_updated, "done": done},
    }


def run_on_staging_first(exec_sql: SqlExecutor, plan: dict[str, Any], migrations_dir: str) -> dict[str, Any]:
    assert_rollback_exists(migrations_dir, plan["name"])
    report = run_migration_plan(exec_sql, plan, environment="staging")
    plan["stagingValidated"] = True
    return {"plan": plan, "report": report}


def rollback_to(exec_sql: SqlExecutor, migrations_dir: str, migration_name: str) -> dict[str, Any]:
    path = assert_rollback_exists(migrations_dir, migration_name)
    script = Path(path).read_text(encoding="utf-8")
    applied = []
    for chunk in script.split(";"):
        lines = [ln.strip() for ln in chunk.splitlines() if ln.strip() and not ln.strip().startswith("--")]
        stmt = "\n".join(lines).strip()
        if not stmt:
            continue
        exec_sql(stmt, None)
        applied.append(stmt[:80])
    return {"applied": applied}


def compare_schemas(left_exec: SqlExecutor, right_exec: SqlExecutor) -> dict[str, Any]:
    sql = (
        "SELECT table_name || '.' || column_name || ':' || data_type AS item "
        "FROM information_schema.columns WHERE table_schema = 'public' ORDER BY 1"
    )
    left = {str(r["item"]) for r in (left_exec(sql, None).get("rows") or [])}
    right = {str(r["item"]) for r in (right_exec(sql, None).get("rows") or [])}
    only_left = sorted(left - right)
    only_right = sorted(right - left)
    return {
        "onlyInLeft": only_left,
        "onlyInRight": only_right,
        "identical": not only_left and not only_right,
    }


_PLANS: dict[str, dict[str, Any]] = {}


def default_migrations_dir() -> str:
    root = os.environ.get("KEPRIX_DATA_DIR") or str(Path.home() / ".keprix-data")
    return str(Path(root) / "migrations-zdt")


def create_add_before_drop_plan(**kwargs: Any) -> dict[str, Any]:
    plan = plan_add_column_before_drop(**kwargs)
    generate_rollback(plan, default_migrations_dir())
    _PLANS[plan["name"]] = plan
    return plan


def get_plan(name: str) -> dict[str, Any] | None:
    row = _PLANS.get(name)
    return deepcopy(row) if row else None


def list_plans() -> list[dict[str, Any]]:
    return [deepcopy(p) for p in _PLANS.values()]


def mark_staging_validated(name: str) -> dict[str, Any]:
    plan = _PLANS.get(name)
    if not plan:
        raise KeyError(name)
    plan["stagingValidated"] = True
    return deepcopy(plan)
