#!/usr/bin/env python3
"""Invoice app example for the Keprix App Foundation SDK."""

from __future__ import annotations

import asyncio
import os
import sqlite3
from pathlib import Path

from keprix_sdk import ActionPlan, KeprixApp, Domain, Entity, ExecutionResult, Field, Operation


DB_PATH = Path(__file__).with_name("invoice_example.db")


def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY, name TEXT, email TEXT, company TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY, client_id INTEGER, amount REAL, currency TEXT, status TEXT)"
    )
    conn.commit()
    return conn


def build_domain() -> Domain:
    return Domain(
        name="invoicing",
        entities=[
            Entity(
                name="Client",
                fields=[
                    Field("name", type="string", required=True),
                    Field("email", type="email", required=True),
                    Field("company", type="string"),
                ],
                operations=[
                    Operation("create"),
                    Operation("read"),
                    Operation("update"),
                    Operation("delete", confirmation_required=True),
                ],
            ),
            Entity(
                name="Invoice",
                fields=[
                    Field("client_id", type="foreign_key", entity="Client", required=True),
                    Field("amount", type="decimal", required=True),
                    Field("currency", type="string", default="GBP"),
                    Field("due_date", type="date"),
                    Field("status", type="enum", values=["draft", "sent", "paid", "overdue"]),
                ],
                operations=[
                    Operation("create"),
                    Operation("read"),
                    Operation("update"),
                    Operation("send", confirmation_required=True),
                    Operation("mark_paid"),
                    Operation("delete", confirmation_required=True),
                ],
            ),
        ],
    )


def execute_plan(conn: sqlite3.Connection, plan: ActionPlan) -> ExecutionResult:
    for step in plan.steps:
        if step.entity == "Client" and step.operation == "create":
            cur = conn.execute(
                "INSERT INTO clients (name, email, company) VALUES (?, ?, ?)",
                (
                    step.fields.get("name", "Unknown"),
                    step.fields.get("email", "unknown@example.com"),
                    step.fields.get("company"),
                ),
            )
            conn.commit()
            step.result = {"id": cur.lastrowid, "status": "created"}
        elif step.entity == "Invoice" and step.operation == "create":
            cur = conn.execute(
                "INSERT INTO invoices (client_id, amount, currency, status) VALUES (?, ?, ?, ?)",
                (1, step.fields.get("amount", 0), step.fields.get("currency", "GBP"), "draft"),
            )
            conn.commit()
            step.result = {"id": cur.lastrowid, "status": "created", "fields": step.fields}
        elif step.entity == "Invoice" and step.operation == "send":
            step.result = {"status": "sent"}
        elif step.entity == "Invoice" and step.operation == "mark_paid":
            conn.execute("UPDATE invoices SET status='paid' WHERE id=(SELECT MAX(id) FROM invoices)")
            conn.commit()
            step.result = {"status": "paid"}
        elif step.operation == "delete":
            step.result = {"status": "deleted", "scope": step.fields.get("scope")}
    return ExecutionResult(success=True, steps=plan.steps)


async def main() -> None:
    conn = init_db()
    app = KeprixApp(
        name="invoice-example",
        keprix_url=os.environ.get("KEPRIX_URL", "http://localhost:3333"),
        api_token=os.environ.get("KEPRIX_API_TOKEN", "demo-token"),
    )
    app.register_domain(build_domain())

    @app.on_action
    def handle_action(plan: ActionPlan) -> ExecutionResult:
        return execute_plan(conn, plan)

    if os.environ.get("KEPRIX_API_TOKEN"):
        app_id = await app.connect()
        print(f"Registered with Keprix: {app_id}")
        plan = await app.handle("create invoice for James £500")
        if plan.requires_confirmation:
            print(plan.confirmation_prompt)
        else:
            result = execute_plan(conn, plan)
            print(result)
    else:
        print("Invoice example ready (set KEPRIX_API_TOKEN to register with a running Keprix server).")
        print("Domain entities: Client, Invoice")


if __name__ == "__main__":
    asyncio.run(main())
