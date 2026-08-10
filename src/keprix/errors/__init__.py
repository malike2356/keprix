"""Public/private error handling (parity with shared/errors)."""

from __future__ import annotations

import re
import traceback
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

REDACT_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "authorization",
    "card_number",
    "credit_card",
    "cvv",
    "cvc",
    "ssn",
}

DEFAULT_MESSAGES: dict[int, str] = {
    400: "Something wasn't right with your request",
    401: "Please log in again",
    403: "You don't have access to that",
    404: "We couldn't find that",
    409: "That change conflicted with a newer update",
    422: "Something wasn't right with your request",
    429: "Too many requests; please slow down and try again",
    500: "Something went wrong on our end; we're on it",
    502: "Something went wrong on our end; we're on it",
    503: "Service temporarily unavailable; please try again shortly",
}

LEAK_PATTERNS = [
    re.compile(r"postgres(ql)?://", re.I),
    re.compile(r"mysql://", re.I),
    re.compile(r"mongodb(\+srv)?://", re.I),
    re.compile(r"redis://", re.I),
    re.compile(r"stack\s*trace", re.I),
    re.compile(r"at\s+\S+\s+\([^)]+\.(ts|js|py):\d+", re.I),
    re.compile(r"/home/|/Users/|/var/www/|C:\\", re.I),
    re.compile(r"ECONNREFUSED|ENOENT|ETIMEDOUT"),
    re.compile(r"API[_-]?KEY|SECRET[_-]?KEY|password\s*=", re.I),
]

_STORE: list[dict[str, Any]] = []
_LISTENERS: list[Callable[[dict[str, Any], dict[str, Any]], None]] = []
SPIKE_WINDOW = timedelta(minutes=5)
SPIKE_THRESHOLD = 10


def get_public_message(status_code: int) -> str:
    return DEFAULT_MESSAGES.get(status_code, DEFAULT_MESSAGES[500])


def is_unsafe_public_message(message: str) -> bool:
    text = str(message or "")
    if not text.strip():
        return True
    return any(p.search(text) for p in LEAK_PATTERNS)


def error_response(status_code: int, public_message: str, error_reference: str) -> dict[str, Any]:
    message = public_message
    if is_unsafe_public_message(message):
        message = get_public_message(status_code)
    return {"error": {"message": message, "reference": error_reference}}


def create_public_error(
    error: BaseException | str | None = None,
    user_message: str | None = None,
    status_code: int = 500,
) -> dict[str, Any]:
    reference = str(uuid.uuid4())
    if status_code >= 500 or not user_message:
        message = get_public_message(status_code)
    else:
        message = user_message.strip()
        if is_unsafe_public_message(message):
            message = get_public_message(status_code)
    _ = error
    return {
        "reference": reference,
        "status_code": status_code,
        "message": message,
        "body": error_response(status_code, message, reference),
    }


def redact_value(value: Any) -> Any:
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            key = re.sub(r"[\s-]+", "_", str(k).lower())
            if key in REDACT_KEYS or "password" in key or "secret" in key or "token" in key:
                out[k] = "[REDACTED]"
            else:
                out[k] = redact_value(v)
        return out
    if isinstance(value, str):
        if re.search(r"sk-[A-Za-z0-9]{10,}", value) or re.search(r"Bearer\s+\S+", value, re.I):
            return "[REDACTED]"
    return value


def detect_five_hundred_spike(
    window: timedelta = SPIKE_WINDOW,
    threshold: int = SPIKE_THRESHOLD,
) -> dict[str, Any]:
    since = datetime.now(timezone.utc) - window
    count = 0
    for row in _STORE:
        if int(row.get("statusCode") or 0) < 500:
            continue
        ts = datetime.fromisoformat(str(row["timestamp"]).replace("Z", "+00:00"))
        if ts >= since:
            count += 1
    triggered = count > threshold
    return {
        "triggered": triggered,
        "count": count,
        "windowMs": int(window.total_seconds() * 1000),
        "threshold": threshold,
        "message": (
            f"Spike: {count} HTTP 5xx errors in {int(window.total_seconds() // 60)} minutes "
            f"(threshold {threshold})"
            if triggered
            else f"OK: {count} HTTP 5xx in window"
        ),
    }


def log_error(
    error: BaseException | str,
    context: dict[str, Any] | None = None,
    error_reference: str | None = None,
) -> dict[str, Any]:
    ctx = context or {}
    if isinstance(error, BaseException):
        message = str(error)
        name = type(error).__name__
        stack = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    else:
        message = str(error)
        name = "Error"
        stack = None
    entry = {
        "errorReference": error_reference or str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "message": message,
        "name": name,
        "stack": stack,
        "route": ctx.get("route"),
        "method": ctx.get("method"),
        "userId": ctx.get("userId"),
        "sessionId": ctx.get("sessionId"),
        "statusCode": int(ctx.get("statusCode") or 500),
        "requestBody": redact_value(ctx.get("requestBody")),
        "environment": ctx.get("environment") or "unknown",
        "frameworkVersion": ctx.get("frameworkVersion"),
        "boundary": ctx.get("boundary"),
        "meta": ctx.get("meta") or {},
    }
    _STORE.append(entry)
    if len(_STORE) > 20_000:
        del _STORE[: len(_STORE) - 15_000]
    spike = detect_five_hundred_spike()
    for fn in list(_LISTENERS):
        try:
            fn(entry, spike)
        except Exception:
            pass
    return entry


def search_errors(filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    f = filters or {}
    limit = min(max(int(f.get("limit") or 100), 1), 500)
    from_ms = datetime.fromisoformat(f["from"].replace("Z", "+00:00")) if f.get("from") else None
    to_ms = datetime.fromisoformat(f["to"].replace("Z", "+00:00")) if f.get("to") else None
    out: list[dict[str, Any]] = []
    for row in reversed(_STORE):
        if len(out) >= limit:
            break
        ts = datetime.fromisoformat(str(row["timestamp"]).replace("Z", "+00:00"))
        if f.get("errorReference") and row["errorReference"] != f["errorReference"]:
            continue
        if f.get("userId") and row.get("userId") != f["userId"]:
            continue
        if f.get("route") and f["route"] not in str(row.get("route") or ""):
            continue
        if f.get("statusCode") is not None and int(row.get("statusCode") or 0) != int(f["statusCode"]):
            continue
        if from_ms and ts < from_ms:
            continue
        if to_ms and ts > to_ms:
            continue
        out.append(row)
    return out


def get_error_context(error_reference: str) -> dict[str, Any] | None:
    for row in reversed(_STORE):
        if row["errorReference"] == error_reference:
            return row
    return None


def on_error_logged(listener: Callable[[dict[str, Any], dict[str, Any]], None]) -> Callable[[], None]:
    _LISTENERS.append(listener)

    def _off() -> None:
        if listener in _LISTENERS:
            _LISTENERS.remove(listener)

    return _off


def clear_error_log_store() -> None:
    _STORE.clear()


def assert_no_stack_in_public_body(body: Any) -> bool:
    raw = str(body)
    if re.search(r"stack", raw, re.I):
        return False
    return not any(p.search(raw) for p in LEAK_PATTERNS)


async def job_error_boundary(job_name: str, job: Callable[[], Awaitable[Any] | Any]) -> dict[str, Any]:
    try:
        value = job()
        if hasattr(value, "__await__"):
            value = await value  # type: ignore[misc]
        return {"ok": True, "value": value}
    except Exception as exc:
        pub = create_public_error(exc, status_code=500)
        log_error(exc, {"boundary": "job", "route": job_name, "statusCode": 500}, pub["reference"])
        return {"ok": False, "reference": pub["reference"]}


async def payment_error_boundary(
    callback_name: str,
    callback: Callable[[], Awaitable[Any] | Any],
) -> dict[str, Any]:
    try:
        value = callback()
        if hasattr(value, "__await__"):
            value = await value  # type: ignore[misc]
        return {"ok": True, "value": value}
    except Exception as exc:
        pub = create_public_error(exc, status_code=500)
        log_error(
            exc,
            {"boundary": "payment", "route": callback_name, "statusCode": 500},
            pub["reference"],
        )
        return {"ok": False, "reference": pub["reference"], "body": pub["body"]}


def install_global_uncaught_handler() -> None:
    import sys
    import threading

    def _hook(exc_type, exc, tb):  # type: ignore[no-untyped-def]
        try:
            log_error(exc or exc_type("unknown"), {"boundary": "uncaughtException", "statusCode": 500})
        finally:
            sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
        if args.exc_value:
            log_error(args.exc_value, {"boundary": "threading", "statusCode": 500})

    threading.excepthook = _thread_hook


def public_http_payload(
    status_code: int,
    detail: Any = None,
    *,
    request_path: str | None = None,
    method: str | None = None,
    request_body: Any = None,
    log_exception: BaseException | None = None,
) -> dict[str, Any]:
    """Build public body and write private log. Safe for FastAPI handlers."""
    user_message: str | None = None
    code = "http_error"
    structured: dict[str, Any] | None = None

    if status_code < 500:
        if isinstance(detail, dict):
            structured = detail
            structured_code = detail.get("code")
            if isinstance(structured_code, str) and structured_code.strip():
                code = structured_code
                user_message = str(
                    detail.get("message")
                    or detail.get("error")
                    or detail.get("detail")
                    or structured_code
                )
            elif "error" in detail:
                user_message = str(detail["error"])
                code = str(detail.get("code") or code)
            else:
                user_message = get_public_message(status_code)
        elif isinstance(detail, str) and detail.strip() and not is_unsafe_public_message(detail):
            user_message = detail
        else:
            user_message = get_public_message(status_code)
        if status_code == 401:
            code = code if code != "http_error" else "unauthorized"
        elif status_code == 403:
            code = code if code != "http_error" else "forbidden"
        elif status_code == 404:
            code = code if code != "http_error" else "not_found"
        elif status_code == 422:
            code = "validation_error"
    else:
        user_message = get_public_message(status_code)
        code = "internal_error"

    pub = create_public_error(log_exception or detail, user_message=user_message, status_code=status_code)
    log_error(
        log_exception or Exception(str(detail)),
        {
            "route": request_path,
            "method": method,
            "statusCode": status_code,
            "requestBody": request_body,
            "boundary": "fastapi",
            "environment": "keprix",
        },
        pub["reference"],
    )
    body = dict(pub["body"])
    # Preserve structured challenge payloads for auth flows without leaking stacks.
    if structured and status_code < 500:
        body["detail"] = structured
        body["code"] = code
    else:
        body["code"] = code
        body["detail"] = body["error"]["message"]
    return body
