"""Published business knowledge for Customer Concierge (Prompt 631).

Operator-selected sources with publish_state/revision. Never the Keprix
self-support corpus or private Brain/Vault.
"""

from __future__ import annotations

import json
import re
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from keprix.customer_concierge.audience.models import _now
from keprix.customer_concierge.store import default_db_path

PublishState = Literal["draft", "published", "archived"]

_SENSITIVE_INTENT_RE = re.compile(
    r"\b(refund|chargeback|lawsuit|solicitor|attorney|legal advice|diagnos|prescri|"
    r"medical advice|password reset|2fa|mfa|account takeover|security incident|"
    r"data breach|hacked)\b",
    re.I,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS concierge_knowledge_sources (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'faq',
    publish_state TEXT NOT NULL DEFAULT 'draft',
    revision INTEGER NOT NULL DEFAULT 1,
    enabled INTEGER NOT NULL DEFAULT 1,
    language TEXT NOT NULL DEFAULT 'en',
    published_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_concierge_knowledge_ws
    ON concierge_knowledge_sources(workspace_id, persona_id, publish_state);

CREATE TABLE IF NOT EXISTS concierge_knowledge_revisions (
    id TEXT PRIMARY KEY,
    entry_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    publish_state TEXT NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(entry_id, revision)
);
"""

_lock = threading.Lock()
_store: KnowledgeStore | None = None


@dataclass
class KnowledgeHit:
    id: str
    title: str
    source_type: str
    excerpt: str
    revision: int
    publish_state: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "type": self.source_type,
            "excerpt": self.excerpt,
            "revision": self.revision,
            "publishState": self.publish_state,
            "confidence": self.confidence,
        }


def detect_sensitive_intent(text: str, extra_patterns: list[str] | None = None) -> str | None:
    m = _SENSITIVE_INTENT_RE.search(text or "")
    if m:
        return m.group(0).lower()
    for pat in extra_patterns or []:
        p = (pat or "").strip()
        if not p:
            continue
        if re.search(p, text or "", re.I):
            return p.lower()
    return None


def build_grounded_answer(
    *,
    query: str,
    hits: list[KnowledgeHit],
    min_confidence: float = 0.45,
    sensitive_patterns: list[str] | None = None,
) -> dict[str, Any]:
    sensitive = detect_sensitive_intent(query, sensitive_patterns)
    if sensitive:
        return {
            "grounded": False,
            "confidence": 0.0,
            "citations": [],
            "excerpts": [],
            "fallbackReason": f"sensitive_intent:{sensitive}",
        }
    if not hits:
        return {
            "grounded": False,
            "confidence": 0.0,
            "citations": [],
            "excerpts": [],
            "fallbackReason": "no_published_match",
        }
    best = max(h.confidence for h in hits)
    citations = [{"id": h.id, "title": h.title, "revision": h.revision} for h in hits[:5]]
    excerpts = [h.excerpt for h in hits[:4]]
    if best < min_confidence:
        return {
            "grounded": False,
            "confidence": best,
            "citations": citations[:3],
            "excerpts": excerpts[:2],
            "fallbackReason": "low_confidence",
        }
    return {
        "grounded": True,
        "confidence": best,
        "citations": citations,
        "excerpts": excerpts,
    }


class KnowledgeStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or default_db_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def upsert_source(
        self,
        *,
        workspace_id: str,
        persona_id: str,
        title: str,
        content: str,
        source_type: str = "faq",
        language: str = "en",
        source_id: str | None = None,
        publish_state: PublishState = "draft",
        created_by: str | None = None,
    ) -> dict[str, Any]:
        now = _now()
        sid = source_id or str(uuid4())
        existing = self.get_source(workspace_id, sid)
        if existing:
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE concierge_knowledge_sources SET
                      title=?, content=?, source_type=?, language=?, updated_at=?
                    WHERE workspace_id=? AND id=?
                    """,
                    (title, content, source_type, language, now, workspace_id, sid),
                )
            row = self.get_source(workspace_id, sid)
            assert row is not None
            return row

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO concierge_knowledge_sources (
                  id, workspace_id, persona_id, title, content, source_type,
                  publish_state, revision, enabled, language, published_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, NULL, ?, ?)
                """,
                (
                    sid,
                    workspace_id,
                    persona_id,
                    title,
                    content,
                    source_type,
                    publish_state,
                    language,
                    now,
                    now,
                ),
            )
            self._conn.execute(
                """
                INSERT INTO concierge_knowledge_revisions (
                  id, entry_id, workspace_id, persona_id, revision, title, content,
                  publish_state, created_by, created_at
                ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    sid,
                    workspace_id,
                    persona_id,
                    title,
                    content,
                    publish_state,
                    created_by,
                    now,
                ),
            )
        row = self.get_source(workspace_id, sid)
        assert row is not None
        return row

    def set_publish_state(
        self,
        *,
        workspace_id: str,
        source_id: str,
        publish_state: PublishState,
        created_by: str | None = None,
    ) -> dict[str, Any] | None:
        row = self.get_source(workspace_id, source_id)
        if not row:
            return None
        now = _now()
        revision = int(row["revision"])
        if publish_state == "published":
            revision += 1
        enabled = 0 if publish_state == "archived" else 1
        published_at = now if publish_state == "published" else row.get("publishedAt")
        with self._conn:
            self._conn.execute(
                """
                UPDATE concierge_knowledge_sources SET
                  publish_state=?, revision=?, enabled=?, published_at=?, updated_at=?
                WHERE workspace_id=? AND id=?
                """,
                (publish_state, revision, enabled, published_at, now, workspace_id, source_id),
            )
            self._conn.execute(
                """
                INSERT OR IGNORE INTO concierge_knowledge_revisions (
                  id, entry_id, workspace_id, persona_id, revision, title, content,
                  publish_state, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    source_id,
                    workspace_id,
                    row["personaId"],
                    revision,
                    row["title"],
                    row["content"],
                    publish_state,
                    created_by,
                    now,
                ),
            )
        return self.get_source(workspace_id, source_id)

    def get_source(self, workspace_id: str, source_id: str) -> dict[str, Any] | None:
        cur = self._conn.execute(
            "SELECT * FROM concierge_knowledge_sources WHERE workspace_id=? AND id=?",
            (workspace_id, source_id),
        )
        row = cur.fetchone()
        return self._map(row) if row else None

    def list_sources(
        self, workspace_id: str, persona_id: str | None = None
    ) -> list[dict[str, Any]]:
        if persona_id:
            cur = self._conn.execute(
                """
                SELECT * FROM concierge_knowledge_sources
                WHERE workspace_id=? AND persona_id=?
                ORDER BY updated_at DESC
                """,
                (workspace_id, persona_id),
            )
        else:
            cur = self._conn.execute(
                """
                SELECT * FROM concierge_knowledge_sources
                WHERE workspace_id=?
                ORDER BY updated_at DESC
                """,
                (workspace_id,),
            )
        return [self._map(r) for r in cur.fetchall()]

    def list_revisions(self, workspace_id: str, source_id: str) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            """
            SELECT revision, title, publish_state, created_by, created_at
            FROM concierge_knowledge_revisions
            WHERE workspace_id=? AND entry_id=?
            ORDER BY revision DESC LIMIT 50
            """,
            (workspace_id, source_id),
        )
        return [
            {
                "revision": int(r["revision"]),
                "title": r["title"],
                "publishState": r["publish_state"],
                "createdBy": r["created_by"],
                "createdAt": r["created_at"],
            }
            for r in cur.fetchall()
        ]

    def search(
        self,
        *,
        workspace_id: str,
        persona_id: str,
        query: str,
        knowledge_source_ids: list[str],
        include_draft: bool = False,
        limit: int = 4,
    ) -> list[KnowledgeHit]:
        ids = [i for i in knowledge_source_ids if i]
        if not ids:
            return []
        states = ["published", "draft"] if include_draft else ["published"]
        terms = [
            t
            for t in re.sub(r"[^a-z0-9\s]", " ", (query or "").lower()).split()
            if len(t) >= 3
        ][:8]

        placeholders = ",".join("?" for _ in ids)
        state_ph = ",".join("?" for _ in states)
        params: list[Any] = [workspace_id, persona_id, *ids, *states]
        where_extra = ""
        if terms:
            clauses = []
            for t in terms:
                clauses.append("(lower(title) LIKE ? OR lower(content) LIKE ?)")
                params.extend([f"%{t}%", f"%{t}%"])
            where_extra = f"AND ({' OR '.join(clauses)})"
        lim = max(1, min(8, limit))
        params.append(lim)
        cur = self._conn.execute(
            f"""
            SELECT * FROM concierge_knowledge_sources
            WHERE workspace_id=? AND persona_id=?
              AND enabled=1
              AND id IN ({placeholders})
              AND publish_state IN ({state_ph})
              {where_extra}
            ORDER BY CASE publish_state WHEN 'published' THEN 0 ELSE 1 END, updated_at DESC
            LIMIT ?
            """,
            params,
        )
        hits: list[KnowledgeHit] = []
        for row in cur.fetchall():
            content = str(row["content"] or "")
            title = str(row["title"] or "Source")
            hay = f"{title}\n{content}".lower()
            match_n = sum(1 for t in terms if t in hay) if terms else 0
            confidence = 0.35 if not terms else min(0.95, 0.35 + match_n / max(1, len(terms)) * 0.6)
            # Draft never qualifies as visitor-grounded even in preview search helpers
            if str(row["publish_state"]) != "published" and not include_draft:
                continue
            hits.append(
                KnowledgeHit(
                    id=str(row["id"]),
                    title=title,
                    source_type=str(row["source_type"] or "faq"),
                    excerpt=content[:500].strip(),
                    revision=int(row["revision"] or 1),
                    publish_state=str(row["publish_state"]),
                    confidence=confidence,
                )
            )
        return hits

    @staticmethod
    def _map(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "workspaceId": str(row["workspace_id"]),
            "personaId": str(row["persona_id"]),
            "title": str(row["title"]),
            "content": str(row["content"]),
            "type": str(row["source_type"]),
            "publishState": str(row["publish_state"]),
            "revision": int(row["revision"] or 1),
            "enabled": bool(row["enabled"]),
            "language": str(row["language"] or "en"),
            "publishedAt": row["published_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "scope": "tenant_customer_knowledge",
            "notProductSupportCorpus": True,
        }


def get_knowledge_store(path: Path | None = None) -> KnowledgeStore:
    global _store
    with _lock:
        if path is not None:
            return KnowledgeStore(path=path)
        if _store is None:
            _store = KnowledgeStore()
        return _store


def reset_knowledge_store_for_tests(path: Path | None = None) -> KnowledgeStore:
    global _store
    with _lock:
        if _store is not None:
            try:
                _store.close()
            except Exception:
                pass
        _store = KnowledgeStore(path=path) if path else KnowledgeStore()
        return _store


def profile_policy(profile: Any) -> dict[str, Any]:
    """Policy knobs from channel_config.policy (confidence, sensitive intents, SLA)."""
    cfg = getattr(profile, "channel_config", None) or {}
    if isinstance(cfg, str):
        try:
            cfg = json.loads(cfg)
        except Exception:
            cfg = {}
    policy = dict(cfg.get("policy") or {})
    return {
        "languages": list(policy.get("languages") or ["en"]),
        "confidenceThreshold": float(policy.get("confidenceThreshold") or 0.45),
        "sensitiveIntents": list(policy.get("sensitiveIntents") or []),
        "slaFirstResponseMinutes": int(policy.get("slaFirstResponseMinutes") or 60),
        "slaResolutionMinutes": int(policy.get("slaResolutionMinutes") or 1440),
        "contactCapture": dict(policy.get("contactCapture") or {"email": True}),
        "bookingEnabled": bool(policy.get("bookingEnabled", True)),
    }


__all__ = [
    "KnowledgeHit",
    "KnowledgeStore",
    "build_grounded_answer",
    "detect_sensitive_intent",
    "get_knowledge_store",
    "profile_policy",
    "reset_knowledge_store_for_tests",
]
