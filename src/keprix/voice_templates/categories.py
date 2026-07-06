"""Built-in voice template categories (generic domain)."""

from __future__ import annotations

from keprix.voice_templates.schemas import CategoryCreate

GENERIC_CATEGORIES: list[CategoryCreate] = [
    CategoryCreate(
        id="greeting",
        label="Greeting",
        description="Opening greeting at start of conversation",
    ),
    CategoryCreate(
        id="confirm_received",
        label="Acknowledged",
        description="Confirm user's message was understood",
    ),
    CategoryCreate(
        id="processing",
        label="Processing",
        description="Agent is working, please wait",
    ),
    CategoryCreate(
        id="response_ready",
        label="Answer ready",
        description="About to give the answer",
    ),
    CategoryCreate(
        id="ask_for_clarification",
        label="Needs clarification",
        description="Need the user to rephrase or add detail",
    ),
    CategoryCreate(
        id="low_confidence",
        label="Low confidence",
        description="Not confident in the answer; suggest English or human help",
    ),
    CategoryCreate(
        id="missing_info_prompt",
        label="Missing information",
        description="A required detail was not provided",
    ),
    CategoryCreate(
        id="confirmation_success",
        label="Done",
        description="Action completed successfully",
    ),
    CategoryCreate(
        id="error_occurred",
        label="Error",
        description="Something went wrong",
    ),
    CategoryCreate(
        id="transfer_to_human",
        label="Transferring",
        description="Routing to a human operator",
    ),
    CategoryCreate(
        id="farewell",
        label="Goodbye",
        description="Closing the conversation",
    ),
    CategoryCreate(
        id="voice_not_available",
        label="Voice unavailable",
        description="This language has no voice output yet; answer is in text",
    ),
]

BOREHOLE_CATEGORIES: list[CategoryCreate] = []

DEFAULT_LANGUAGE_FALLBACKS: dict[str, str] = {
    "fan-gh": "ak-gh",
    "dag-gh": "ak-gh",
}
