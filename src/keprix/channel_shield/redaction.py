"""Neutralise untrusted channel content before any agent-facing surface."""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse

# Patterns that must never reach assistants, skills, playbooks, or memory writers.
_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"ignore\s+(?:\w+\s+)*(previous|all|above|prior)\s+(?:\w+\s+)*instructions",
            re.IGNORECASE,
        ),
        "[redacted:prompt-injection]",
    ),
    (
        re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
        "[redacted:prompt-injection]",
    ),
    (
        re.compile(
            r"disregard\s+(?:\w+\s+)*(your|all|any)\s+(?:\w+\s+)*(instructions|rules)",
            re.IGNORECASE,
        ),
        "[redacted:prompt-injection]",
    ),
    (
        re.compile(r"<!--[\s\S]*?-->", re.IGNORECASE),
        "[redacted:html-comment]",
    ),
    (
        re.compile(
            r"<\s*div\s+[^>]*style\s*=\s*[\"'][^\"']*display\s*:\s*none[^\"']*[\"'][^>]*>[\s\S]*?</\s*div\s*>",
            re.IGNORECASE,
        ),
        "[redacted:hidden-html]",
    ),
    (
        re.compile(r"powershell\s+-enc\s+\S+", re.IGNORECASE),
        "[redacted:encoded-command]",
    ),
    (
        re.compile(r"(?:base64|b64)\s*[:=]\s*[A-Za-z0-9+/=]{24,}", re.IGNORECASE),
        "[redacted:encoded-payload]",
    ),
    (
        re.compile(
            r"(password|passwd|api[_-]?key|secret|token)\s*[:=]\s*\S+",
            re.IGNORECASE,
        ),
        "[redacted:credential-bait]",
    ),
    (
        re.compile(
            r"(send|wire|transfer)\s+(?:me\s+)?(?:your\s+)?(?:password|credentials|bank|gift\s*card)",
            re.IGNORECASE,
        ),
        "[redacted:credential-request]",
    ),
    (
        re.compile(r"https?://\d{1,3}(?:\.\d{1,3}){3}\S*", re.IGNORECASE),
        "[redacted:ip-url]",
    ),
    (
        re.compile(
            r"(tool_call|function_call|invoke_tool)\s*\([^)]*\)",
            re.IGNORECASE,
        ),
        "[redacted:tool-bait]",
    ),
]

_TRACKING_PIXEL = re.compile(
    r"<img[^>]*(?:width|height)\s*=\s*[\"']?1[\"']?[^>]*>",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_SUSPICIOUS_TLDS = (".zip", ".mov", ".top", ".xyz", ".ru", ".cn", ".tk", ".gq")


def scrub_filename(name: str) -> str:
    base = (name or "attachment").replace("\x00", "")
    base = re.sub(r"[^\w.\- ]+", "_", base)[:120]
    lower = base.lower()
    if any(lower.endswith(ext) for ext in (".exe", ".scr", ".js", ".vbs", ".hta", ".iso", ".lnk")):
        return f"{base}.quarantined"
    return base or "attachment"


def scrub_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        return "[redacted:url]"
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
        return f"[redacted-host:{host}]"
    if any(host.endswith(tld) for tld in _SUSPICIOUS_TLDS):
        return f"[suspect-host:{host}]"
    return f"https://{host}/[path-redacted]"


def extract_domains(text: str, links: list[str] | None = None) -> list[str]:
    urls = list(links or [])
    urls.extend(_URL_RE.findall(text or ""))
    domains: list[str] = []
    for url in urls:
        host = urlparse(url).hostname
        if host and host not in domains:
            domains.append(host.lower())
    return domains


def redact_text(text: str) -> tuple[str, list[str]]:
    """Return redacted text and a list of redaction reasons applied."""
    if not text:
        return "", []
    out = html.unescape(text)
    reasons: list[str] = []
    out = _TRACKING_PIXEL.sub("[redacted:tracking-pixel]", out)
    if "[redacted:tracking-pixel]" in out:
        reasons.append("tracking-pixel")
    for pattern, replacement in _INJECTION_PATTERNS:
        if pattern.search(out):
            out = pattern.sub(replacement, out)
            tag = replacement.strip("[]")
            if tag not in reasons:
                reasons.append(tag)
    # Neutralise remaining URLs after pattern pass
    def _url_sub(match: re.Match[str]) -> str:
        if "url-scrub" not in reasons:
            reasons.append("url-scrub")
        return scrub_url(match.group(0))

    out = _URL_RE.sub(_url_sub, out)
    # Strip residual HTML tags
    out = re.sub(r"<[^>]+>", " ", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out, reasons
