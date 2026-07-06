"""Email MCP server exposing agent tools."""

from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp.types import TextContent, Tool

from keprix.email.helpers import send_smtp_message
from keprix.email.store import get_email_store

server = Server("keprix-email")


def _tools() -> list[Tool]:
    return [
        Tool(
            name="list_emails",
            description="List emails from inbox with optional unread filter",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "default": "INBOX"},
                    "limit": {"type": "integer", "default": 20},
                    "unread_only": {"type": "boolean", "default": False},
                    "user_id": {"type": "string", "default": "local"},
                },
            },
        ),
        Tool(
            name="read_email",
            description="Read a single email by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "user_id": {"type": "string", "default": "local"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="send_email",
            description="Send an email directly",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "user_id": {"type": "string", "default": "local"},
                },
                "required": ["to", "subject", "body"],
            },
        ),
        Tool(
            name="create_draft",
            description="Create an email draft without sending",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "user_id": {"type": "string", "default": "local"},
                },
                "required": ["to", "subject", "body"],
            },
        ),
        Tool(
            name="mark_read",
            description="Mark an email as read",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "user_id": {"type": "string", "default": "local"},
                },
                "required": ["id"],
            },
        ),
        Tool(
            name="search_emails",
            description="Search emails by subject, body, or AI tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 20},
                    "user_id": {"type": "string", "default": "local"},
                },
                "required": ["query"],
            },
        ),
    ]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return _tools()


async def _handle_tool(name: str, arguments: dict[str, Any]) -> str:
    store = get_email_store()
    user_id = str(arguments.get("user_id", "local"))

    if name == "list_emails":
        unread = bool(arguments.get("unread_only", False))
        limit = int(arguments.get("limit", 20))
        rows = await store.list_emails(user_id, unread=unread if unread else None, limit=limit)
        return json.dumps([r.to_dict() for r in rows], default=str)

    if name == "read_email":
        record = await store.get_email(str(arguments["id"]), user_id)
        if record is None:
            return json.dumps({"error": "not found"})
        return json.dumps(record.to_dict(), default=str)

    if name == "search_emails":
        rows = await store.search_emails(
            user_id, str(arguments["query"]), limit=int(arguments.get("limit", 20))
        )
        return json.dumps([r.to_dict() for r in rows], default=str)

    if name == "mark_read":
        record = await store.update_email(str(arguments["id"]), user_id, {"is_read": True})
        return json.dumps({"ok": record is not None})

    if name == "create_draft":
        draft = await store.create_draft(
            user_id,
            {
                "to_addresses": [str(arguments["to"])],
                "subject": str(arguments["subject"]),
                "body": str(arguments["body"]),
            },
        )
        return json.dumps(draft.to_dict(), default=str)

    if name == "send_email":
        accounts = await store.list_accounts(user_id)
        if not accounts:
            return json.dumps({"error": "no account"})
        account = accounts[0]
        send_smtp_message(
            account.to_connection(),
            from_addr=account.email_address,
            to_addresses=[str(arguments["to"])],
            cc_addresses=[],
            subject=str(arguments["subject"]),
            body=str(arguments["body"]),
        )
        return json.dumps({"status": "sent"})

    return json.dumps({"error": f"unknown tool {name}"})


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    payload = await _handle_tool(name, arguments or {})
    return [TextContent(type="text", text=payload)]


def get_mcp_server() -> Server:
    return server
