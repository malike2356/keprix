"""Knowledge base helpers for support operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.support.store import get_support_store


def _articles_path():
    return get_support_store()._dir / "knowledge.json"


def list_articles() -> list[dict[str, Any]]:
    path = _articles_path()
    if not path.exists():
        return []
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def save_article(*, title: str, body: str, source_ticket_id: str | None = None) -> dict[str, Any]:
    import json

    articles = list_articles()
    article = {
        "id": str(uuid.uuid4()),
        "title": title,
        "body": body,
        "source_ticket_id": source_ticket_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    articles.append(article)
    path = _articles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(articles, indent=2), encoding="utf-8")
    return article


def article_from_ticket(ticket_id: str) -> dict[str, Any] | None:
    ticket = get_support_store().get_ticket(ticket_id)
    if ticket is None:
        return None
    title = f"Resolved: {ticket.get('subject', 'Support ticket')}"
    body = ticket.get("description") or ""
    return save_article(title=title, body=body, source_ticket_id=ticket_id)


def search_articles(query: str) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return list_articles()
    return [
        article
        for article in list_articles()
        if q in article.get("title", "").lower() or q in article.get("body", "").lower()
    ]
