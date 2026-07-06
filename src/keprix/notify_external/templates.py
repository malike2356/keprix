"""Built-in external notification templates."""

from __future__ import annotations

import re
from typing import Any


class SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "[missing]"


TEMPLATES: dict[str, dict[str, str]] = {
    "review_request": {
        "subject": "[Action needed] {title} - review required by {expires_date}",
        "text": (
            "You have been asked to review: {title}\n\n"
            "{context_message}\n\n"
            "Review and decide here:\n{review_url}\n\n"
            "This link expires: {expires_at}\n"
            "Sent by: {workspace_name}\n"
        ),
        "html": (
            "<p>You have been asked to review: <strong>{title}</strong></p>"
            "<p>{context_message}</p>"
            "<p><a href=\"{review_url}\">Review and decide</a></p>"
            "<p>This link expires: {expires_at}</p>"
            "<p>Sent by: {workspace_name}</p>"
        ),
    },
    "review_reminder": {
        "subject": "[Reminder] {title} - review still pending",
        "text": (
            "Reminder: review still pending for {title}.\n\n"
            "{context_message}\n\n"
            "Review here: {review_url}\n"
            "Expires: {expires_at}\n"
        ),
        "html": (
            "<p>Reminder: review still pending for <strong>{title}</strong>.</p>"
            "<p>{context_message}</p>"
            "<p><a href=\"{review_url}\">Review and decide</a></p>"
        ),
    },
    "review_receipt": {
        "subject": "Your decision has been recorded: {title}",
        "text": (
            "Your decision for '{title}' has been recorded.\n\n"
            "Decision: {action}\n"
            "Recorded at: {decided_at}\n"
            "Reference: {review_request_id}\n"
        ),
        "html": (
            "<p>Your decision for <strong>{title}</strong> has been recorded.</p>"
            "<p>Decision: {action}</p>"
            "<p>Recorded at: {decided_at}</p>"
        ),
    },
    "pack_gate_pending": {
        "subject": "[Approval needed] {pack_name} v{version} is awaiting your sign-off",
        "text": (
            "Pack {pack_name} version {version} is awaiting your sign-off.\n\n"
            "{message}\n\n"
            "Sign off here: {sign_off_url}\n"
        ),
        "html": (
            "<p>Pack <strong>{pack_name}</strong> version {version} is awaiting your sign-off.</p>"
            "<p>{message}</p>"
            "<p><a href=\"{sign_off_url}\">Open sign-off page</a></p>"
        ),
    },
    "generic_alert": {
        "subject": "[Keprix] {title}",
        "text": "{message}\n\n{href}\n",
        "html": "<p><strong>{title}</strong></p><p>{message}</p><p>{href}</p>",
    },
    "evidence_pack_ready": {
        "subject": "Evidence pack ready: {date_from} to {date_to}",
        "text": (
            "An evidence pack is ready for download.\n\n"
            "Period: {date_from} to {date_to}\n"
            "Events: {event_count}\n"
            "Download: {download_url}\n"
        ),
        "html": (
            "<p>An evidence pack is ready.</p>"
            "<p>Period: {date_from} to {date_to}</p>"
            "<p><a href=\"{download_url}\">Download pack</a></p>"
        ),
    },
}

_DANGEROUS_TAGS = re.compile(r"<\s*(script|iframe|object|embed)\b", re.I)
_EVENT_ATTRS = re.compile(r"\s+on\w+\s*=", re.I)


def render_template(name: str, variables: dict[str, Any], *, custom: dict[str, str] | None = None) -> dict[str, str]:
    source = custom or TEMPLATES.get(name)
    if source is None:
        raise ValueError(f"Unknown template: {name}")
    mapping = SafeFormatDict(**{key: str(value) for key, value in variables.items()})
    return {
        "subject": source["subject"].format_map(mapping),
        "text": source["text"].format_map(mapping),
        "html": source.get("html", "").format_map(mapping),
    }


def sanitize_template_html(html: str) -> str:
    if _DANGEROUS_TAGS.search(html):
        raise ValueError("Template HTML contains disallowed tags")
    if _EVENT_ATTRS.search(html):
        raise ValueError("Template HTML contains event handler attributes")
    return html


def list_template_names() -> list[str]:
    return sorted(TEMPLATES.keys())
