"""Time-aware greeting utilities for the home page GreetingBar.

Produces a context-appropriate greeting based on the local hour.
"""

from __future__ import annotations


def get_greeting(hour: int) -> str:
    """Return the appropriate greeting for the given hour (0-23).

    Args:
        hour: Hour in 24-hour format, in the user's local timezone.
    """
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 18:
        return "Good afternoon"
    if 18 <= hour < 22:
        return "Good evening"
    return "Working late"


SUGGESTION_CHIPS: dict[str, list[str]] = {
    "keprix": [
        "Help me draft a reply to a client email",
        "Summarise the documents I uploaded last week",
        "Research the top borehole contractors in Accra",
        "Set a reminder to follow up with James on Thursday",
    ],
    "aiva": [
        "Find the latest messages from Kofi and draft a reply",
        "Book an appointment for tomorrow at 2pm",
        "Summarise all follow-ups due this week",
        "Draft a proposal for the new client inquiry",
    ],
    "abbis": [
        "List the top property listings added this week",
        "Generate a borehole survey report for site AB-12",
        "Find all documents pending approval",
        "Summarise the latest regulatory updates for Accra region",
    ],
}


def get_suggestion_chips(surface: str) -> list[str]:
    """Return suggestion chips appropriate for the given product surface."""
    return SUGGESTION_CHIPS.get(surface, SUGGESTION_CHIPS["keprix"])
