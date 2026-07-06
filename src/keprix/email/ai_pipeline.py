"""Background AI processing for new emails."""

from __future__ import annotations

import asyncio
import logging

from keprix.email.llm import summarize_email
from keprix.email.store import EmailRecord, get_email_store

logger = logging.getLogger(__name__)


async def process_new_email(email: EmailRecord) -> None:
    store = get_email_store()
    try:
        result = await summarize_email(
            email.subject,
            email.body_text or email.preview or "",
            email.from_address,
        )
        await store.update_email(
            email.id,
            email.user_id,
            {
                "ai_summary": result.get("summary"),
                "ai_tags": result.get("tags", []),
                "ai_priority": result.get("priority", "normal"),
            },
        )
    except Exception:
        logger.exception("Email AI pipeline failed for %s", email.id)


def schedule_email_ai(email: EmailRecord) -> None:
    asyncio.create_task(process_new_email(email))
