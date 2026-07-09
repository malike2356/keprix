#!/usr/bin/env python3
"""CRM app example for the Keprix App Foundation SDK."""

from __future__ import annotations

import asyncio
import os
import sqlite3
from pathlib import Path

from keprix_sdk import ActionPlan, KeprixApp, Domain, Entity, ExecutionResult, Field, Operation


DB_PATH = Path(__file__).with_name("crm_example.db")


def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, name TEXT, email TEXT, company TEXT)"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS companies (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS deals (id INTEGER PRIMARY KEY, contact_id INTEGER, title TEXT, value REAL, stage TEXT)"
    )
    conn.commit()
    return conn


def build_domain() -> Domain:
    return Domain(
        name="crm",
        entities=[
            Entity(
                name="Contact",
                fields=[
                    Field("name", type="string", required=True),
                    Field("email", type="email"),
                    Field("company", type="string"),
                ],
                operations=[Operation("create"), Operation("read"), Operation("update"), Operation("delete", confirmation_required=True)],
            ),
            Entity(
                name="Company",
                fields=[Field("name", type="string", required=True)],
                operations=[Operation("create"), Operation("read"), Operation("update")],
            ),
            Entity(
                name="Deal",
                fields=[
                    Field("contact_id", type="foreign_key", entity="Contact"),
                    Field("title", type="string", required=True),
                    Field("value", type="decimal"),
                    Field("stage", type="enum", values=["lead", "qualified", "won", "lost"]),
                ],
                operations=[Operation("create"), Operation("read"), Operation("update")],
            ),
        ],
    )


def execute_plan(conn: sqlite3.Connection, plan: ActionPlan) -> ExecutionResult:
    for step in plan.steps:
        if step.entity == "Contact" and step.operation == "create":
            cur = conn.execute(
                "INSERT INTO contacts (name, email, company) VALUES (?, ?, ?)",
                (step.fields.get("name", "Unknown"), step.fields.get("email"), step.fields.get("company")),
            )
            conn.commit()
            step.result = {"id": cur.lastrowid, "status": "created"}
        elif step.entity == "Deal" and step.operation == "create":
            cur = conn.execute(
                "INSERT INTO deals (contact_id, title, value, stage) VALUES (?, ?, ?, ?)",
                (1, step.fields.get("title", "New deal"), step.fields.get("value", 0), "lead"),
            )
            conn.commit()
            step.result = {"id": cur.lastrowid, "status": "created"}
        elif step.operation == "delete":
            step.result = {"status": "deleted", "scope": step.fields.get("scope")}
    return ExecutionResult(success=True, steps=plan.steps)


async def main() -> None:
    conn = init_db()
    app = KeprixApp(
        name="crm-example",
        keprix_url=os.environ.get("KEPRIX_URL", "http://localhost:3333"),
        api_token=os.environ.get("KEPRIX_API_TOKEN", "demo-token"),
    )
    app.register_domain(build_domain())

    @app.on_action
    def handle_action(plan: ActionPlan) -> ExecutionResult:
        return execute_plan(conn, plan)

    if os.environ.get("KEPRIX_API_TOKEN"):
        app_id = await app.connect()
        print(f"Registered CRM app: {app_id}")
    else:
        print("CRM example ready (set KEPRIX_API_TOKEN to register with Keprix).")
        print("Domain entities: Contact, Company, Deal")


if __name__ == "__main__":
    asyncio.run(main())
