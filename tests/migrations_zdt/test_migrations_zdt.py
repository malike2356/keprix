"""Zero-downtime migration tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

from keprix.migrations_zdt import (
    assert_add_before_drop,
    compare_schemas,
    generate_rollback,
    plan_add_column_before_drop,
    production_confirmation_gate,
    rollback_to,
    run_on_staging_first,
)


def _memory():
    columns = {"id", "email_old"}
    table = [
        {"id": 1, "email_old": "a@example.com", "email_new": None},
        {"id": 2, "email_old": "b@example.com", "email_new": None},
    ]

    def exec_sql(sql: str, _params=None):
        if "ADD COLUMN" in sql.upper() and "email_new" in sql:
            columns.add("email_new")
            return {"rows": [], "rowCount": 0, "lockMs": 4}
        if "SET" in sql.upper() and "email_new" in sql:
            updated = 0
            for row in table:
                if row.get("email_new") != row.get("email_old"):
                    row["email_new"] = row["email_old"]
                    updated += 1
            return {"rows": [], "rowCount": updated, "lockMs": 5}
        if "mismatches" in sql:
            mismatches = sum(1 for r in table if r.get("email_new") != r.get("email_old"))
            return {"rows": [{"mismatches": mismatches}], "rowCount": 1, "lockMs": 1}
        if "DROP COLUMN" in sql.upper() and "email_old" in sql:
            columns.discard("email_old")
            for row in table:
                row.pop("email_old", None)
            return {"rows": [], "rowCount": 0, "lockMs": 3}
        if "DROP COLUMN" in sql.upper() and "email_new" in sql:
            columns.discard("email_new")
            for row in table:
                row.pop("email_new", None)
            return {"rows": [], "rowCount": 0, "lockMs": 3}
        if "ADD COLUMN" in sql.upper() and "email_old" in sql:
            columns.add("email_old")
            for row in table:
                row.setdefault("email_old", row.get("email_new"))
            return {"rows": [], "rowCount": 0, "lockMs": 3}
        if "information_schema.columns" in sql:
            items = [{"item": f"users.{c}:text"} for c in sorted(columns)]
            return {"rows": items, "rowCount": len(items), "lockMs": 1}
        return {"rows": [], "rowCount": 0, "lockMs": 1}

    return exec_sql, lambda: sorted(columns)


def test_reject_drop_first():
    try:
        assert_add_before_drop(
            [
                {"kind": "drop_column"},
                {"kind": "add_column"},
            ]
        )
        assert False, "expected error"
    except ValueError:
        pass


def test_staging_then_rollback_identity():
    with tempfile.TemporaryDirectory() as tmp:
        plan = plan_add_column_before_drop(
            name="users_email_zdt",
            table="users",
            old_column="email_old",
            new_column={"name": "email_new", "typeSql": "TEXT"},
        )
        generate_rollback(plan, tmp)
        assert Path(tmp, "users_email_zdt.rollback.sql").exists()

        exec_sql, schema = _memory()
        baseline = _memory()
        out = run_on_staging_first(exec_sql, plan, tmp)
        assert out["plan"]["stagingValidated"] is True
        assert "email_new" in schema()
        assert "email_old" not in schema()

        gate = production_confirmation_gate(out["plan"])
        assert gate["allowed"] is False

        rollback_to(exec_sql, tmp, plan["name"])
        diff = compare_schemas(baseline[0], exec_sql)
        assert diff["identical"] is True
