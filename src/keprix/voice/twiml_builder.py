"""TwiML response helpers for Aiva phone voice."""

from __future__ import annotations

from html import escape


def connect_stream_response(*, stream_url: str, greeting: str | None = None, call_sid: str | None = None) -> str:
    say = f"<Say>{escape(greeting)}</Say>" if greeting else ""
    attrs = f' url="{escape(stream_url)}"'
    if call_sid:
        attrs += f' name="{escape(call_sid)}"'
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{say}"
        "<Connect>"
        f"<Stream{attrs} />"
        "</Connect>"
        "</Response>"
    )


def reject_response(reason: str = "rejected") -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Reject reason="{escape(reason)}" /></Response>'


def dial_transfer_response(number: str, handoff: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Say>{escape(handoff)}</Say>"
        f"<Dial>{escape(number)}</Dial>"
        "</Response>"
    )
