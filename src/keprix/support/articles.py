"""Help articles, newsletter, and release note templates."""

from __future__ import annotations

from typing import Any

RELEASE_NOTE_TEMPLATE = """# Keprix {version}

## Highlights
- 

## Fixes
- 

## Upgrade notes
- 

## Community
Questions and bug reports: https://github.com/malike2356/keprix/issues
"""

NEWSLETTER_TEMPLATE = """# Keprix community update

## What shipped
- 

## Tips for self-hosters
- 

## Get help
- Docs: https://keprixai.com/docs
- GitHub issues: https://github.com/malike2356/keprix/issues

_Note: Keprix is MIT-licensed self-host software. Paid commercial support is not included._
"""

SETUP_RESCUE_STEPS = [
    {
        "id": "check-health",
        "title": "Run health checks",
        "detail": "Open Support and download a diagnostics bundle, or visit Admin diagnostics.",
    },
    {
        "id": "verify-provider",
        "title": "Verify LLM provider",
        "detail": "Confirm API keys are in Vault and provider health passes.",
    },
    {
        "id": "review-logs",
        "title": "Review redacted errors",
        "detail": "Attach only redacted diagnostics when opening a community issue.",
    },
    {
        "id": "backup-before-change",
        "title": "Backup before recovery",
        "detail": "Export backup from Admin before retrying restore or reinstall steps.",
    },
]

COMMUNITY_LINKS = [
    {"label": "Documentation", "url": "https://keprixai.com/docs"},
    {"label": "GitHub issues", "url": "https://github.com/malike2356/keprix/issues"},
    {"label": "Contributing guide", "url": "https://github.com/malike2356/keprix/blob/main/CONTRIBUTING.md"},
    {"label": "Security disclosures", "url": "https://github.com/malike2356/keprix/blob/main/SECURITY.md"},
]


def list_templates() -> dict[str, Any]:
    return {
        "release_note": RELEASE_NOTE_TEMPLATE,
        "newsletter": NEWSLETTER_TEMPLATE,
        "setup_rescue": SETUP_RESCUE_STEPS,
        "community_links": COMMUNITY_LINKS,
    }
