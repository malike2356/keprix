"""Retry original task after tool installation."""

from __future__ import annotations

import json
import re
from typing import Any


class KeprixRetry:
    async def retry(
        self,
        *,
        original_message: str,
        tool_name: str,
        session_id: str | None = None,
    ) -> str:
        _ = session_id
        try:
            from tools.registry import registry

            entry = registry.get_entry(tool_name)
            if entry is None:
                return f"Tool installed, but {tool_name} is not yet available in the registry."

            payload = _infer_handler_payload(tool_name, original_message, entry)
            raw = registry.dispatch(tool_name, payload, store=None)
            return _format_retry_message(tool_name, raw)
        except Exception as exc:
            return f"Retry attempted after install, but execution failed: {exc}"


def _infer_handler_payload(tool_name: str, original_message: str, entry: Any) -> dict[str, Any]:
    if tool_name == "fetch_stock_price":
        return {"ticker": _extract_stock_ticker(original_message)}

    if tool_name == "track_time":
        project = _extract_track_time_project(original_message)
        lowered = original_message.lower()
        if re.search(r"\bstop\b", lowered):
            return {"project": project, "action": "stop"}
        if re.search(r"\blog\b", lowered) or re.search(r"\b\d+\s*(?:min|minute|hour)", lowered):
            minutes = _extract_minutes(original_message)
            if minutes is not None:
                return {"project": project, "action": "log", "minutes": minutes}
        return {"project": project, "action": "start"}

    schema = getattr(entry, "schema", None) or {}
    parameters = schema.get("parameters") if isinstance(schema, dict) else {}
    properties = parameters.get("properties", {}) if isinstance(parameters, dict) else {}
    required = parameters.get("required", []) if isinstance(parameters, dict) else []
    if not required:
        return {}
    if "query" in properties:
        return {"query": original_message}
    if len(required) == 1:
        return {required[0]: original_message}
    return {"query": original_message}


def _extract_stock_ticker(message: str) -> str:
    upper = message.upper()
    skip = {"FETCH", "GET", "WHAT", "STOCK", "PRICE", "THE", "FOR", "A", "AN", "MY", "AT", "IS"}
    for candidate in re.findall(r"\b([A-Z]{1,5})\b", upper):
        if candidate not in skip:
            return candidate
    return "AAPL"


def _extract_track_time_project(message: str) -> str:
    quoted = re.search(r'"([^"]+)"|\'([^\']+)\'', message)
    if quoted:
        return (quoted.group(1) or quoted.group(2) or "").strip() or "default"
    on_match = re.search(r"\bon\s+(.+?)(?:[.?!]|$)", message, re.IGNORECASE)
    if on_match:
        project = on_match.group(1).strip()
        if project:
            return project
    return "default"


def _extract_minutes(message: str) -> float | None:
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:min(?:ute)?s?|hrs?|hours?)\b", message, re.IGNORECASE)
    if not match:
        return None
    value = float(match.group(1))
    if "hour" in match.group(0).lower() or "hr" in match.group(0).lower():
        return value * 60.0
    return value


def _format_retry_message(tool_name: str, raw: str) -> str:
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return f"Retry complete. Tool response: {raw}"

    if isinstance(payload, dict) and payload.get("error"):
        return f"Retry failed: {payload['error']}"

    if tool_name == "fetch_stock_price":
        ticker = str(payload.get("ticker") or "stock")
        price = payload.get("price")
        if price is not None:
            return f"Retry complete. {ticker} is currently trading at ${float(price):.2f}."
        if payload.get("success"):
            return f"Retry complete. Stock lookup succeeded for {ticker}."

    if tool_name == "track_time":
        project = str(payload.get("project") or "project")
        action = str(payload.get("action") or "log")
        if action == "start":
            return f"Retry complete. Timer started for {project}."
        if action == "stop":
            minutes = payload.get("minutes")
            if minutes is not None:
                return f"Retry complete. Logged {minutes} minutes for {project}."
            return f"Retry complete. Timer stopped for {project}."
        minutes = payload.get("minutes")
        if minutes is not None:
            return f"Retry complete. Logged {minutes} minutes for {project}."

    if isinstance(payload, dict) and payload.get("success"):
        summary = ", ".join(f"{key}={value}" for key, value in payload.items() if key != "success")
        return f"Retry complete. {summary or 'Tool executed successfully.'}."
    return f"Retry complete. Tool response: {raw}"
