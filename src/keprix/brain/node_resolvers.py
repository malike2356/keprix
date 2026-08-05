"""Content resolvers for brain graph node kinds."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from keprix.brain.graph_types import GraphNode, NODE_KINDS
from keprix_constants import get_keprix_home


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _short(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "..."


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


class NodeResolver:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], dict[str, Any]] = {}
        self.owner_user_ids: list[str] = []

    def seed(self, workspace_id: str, kind: str, node_id: str, record: dict[str, Any]) -> None:
        self._records[(workspace_id, kind, node_id)] = record

    async def resolve(self, workspace_id: str, kind: str, node_id: str) -> GraphNode | None:
        if kind not in NODE_KINDS:
            return None
        record = self._records.get((workspace_id, kind, node_id))
        if record is not None:
            return self._from_record(kind, node_id, record)
        if kind == "tool":
            return GraphNode(
                id=node_id,
                kind=kind,
                label=node_id.replace("_", " ").replace("-", " ").title(),
                summary=f"Keprix tool `{node_id}`",
                created_at=_now(),
                metadata={"registry": "builtin"},
                content={"id": node_id},
            )
        if kind == "session":
            return await self._resolve_session(workspace_id, node_id)
        if kind == "memory":
            return await self._resolve_memory(workspace_id, node_id)
        if kind == "entity":
            return await self._resolve_entity(workspace_id, node_id)
        if kind == "skill":
            return await self._resolve_skill(workspace_id, node_id)
        if kind == "document":
            return await self._resolve_document(workspace_id, node_id)
        if kind == "source":
            return await self._resolve_source(workspace_id, node_id)
        if kind == "task":
            return await self._resolve_task(workspace_id, node_id)
        return None

    def tombstone(self, kind: str, node_id: str) -> GraphNode:
        return GraphNode(
            id=node_id,
            kind=kind,
            label="[deleted]",
            summary="Source record is unavailable, but graph edges are preserved.",
            created_at=_now(),
            metadata={},
            deleted=True,
            content={},
        )

    async def _resolve_session(self, workspace_id: str, session_id: str) -> GraphNode | None:
        if session_id == "memory-hub":
            return self._from_record(
                "session",
                session_id,
                {
                    "title": "Memory vault",
                    "summary": "Hub for episodic memories and Temporal KG entities.",
                    "metadata": {"source": "memory_overlay", "workspace_id": workspace_id},
                    "content": {"id": session_id, "title": "Memory vault", "virtual": True},
                },
            )
        try:
            from keprix.workspace.repository import workspace_repo

            for session in workspace_repo.sessions.values():
                if str(session.get("id")) == session_id:
                    title = str(session.get("title") or "Session")
                    return self._from_record(
                        "session",
                        session_id,
                        {
                            "title": title,
                            "summary": title,
                            "created_at": session.get("created_at"),
                            "updated_at": session.get("updated_at"),
                            "metadata": {"workspace_id": workspace_id, "source": "workspace_repo"},
                            "content": {"id": session_id, "title": title, "message_count": len(session.get("messages") or [])},
                        },
                    )
        except Exception:
            pass

        row = self._data_plane_session(workspace_id, session_id)
        if row:
            title = str(row.get("title") or "Session")
            return self._from_record(
                "session",
                session_id,
                {
                    "title": title,
                    "summary": title,
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                    "metadata": {"workspace_id": workspace_id, "source": "data_plane"},
                    "content": row,
                },
            )

        vault = self._vault_conversation(session_id)
        if vault:
            return vault
        return None

    async def _resolve_memory(self, workspace_id: str, memory_id: str) -> GraphNode | None:
        home = get_keprix_home()
        candidates = [
            home / "memories" / f"{memory_id}.md",
            home / "memories" / f"{memory_id}.json",
            home / "brain" / "memories" / f"{memory_id}.md",
        ]
        for path in candidates:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if path.suffix == ".json":
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    continue
                return self._from_record("memory", memory_id, data if isinstance(data, dict) else {"content": text})
            return self._from_record("memory", memory_id, {"content": text, "title": path.stem})

        # Fall back to episodic PG / in-memory store (hub control plane).
        try:
            from keprix.memory.episodic.store import create_episodic_store

            store = create_episodic_store()
            owners = list(dict.fromkeys([*self.owner_user_ids, workspace_id, "default"]))
            for user_id in owners:
                for memory in await store.list_all(user_id):
                    if memory.id == memory_id:
                        meta = dict(memory.metadata or {})
                        title = str(meta.get("title") or _short(memory.content, 48) or memory_id)
                        return self._from_record(
                            "memory",
                            memory_id,
                            {
                                "title": title,
                                "summary": _short(memory.content, 160),
                                "content": memory.content,
                                "created_at": memory.created_at,
                                "metadata": {
                                    **meta,
                                    "source": meta.get("source") or "episodic",
                                    "tags": memory.tags,
                                    "workspace_id": workspace_id,
                                    "owner_user_id": user_id,
                                },
                            },
                        )
        except Exception:
            pass
        return None

    async def _resolve_entity(self, workspace_id: str, entity_id: str) -> GraphNode | None:
        try:
            from keprix.memory.temporal_kg import TemporalKnowledgeGraph

            kg = TemporalKnowledgeGraph()
            owners = list(dict.fromkeys([*self.owner_user_ids, workspace_id, "default"]))
            for user_id in owners:
                graph = await kg.search(user_id, "", limit=200)
                for entity in graph.get("entities") or []:
                    if str(entity.get("id")) == entity_id:
                        name = str(entity.get("name") or entity_id)
                        return self._from_record(
                            "entity",
                            entity_id,
                            {
                                "title": name,
                                "summary": f"{entity.get('entity_type') or 'thing'} · {entity.get('belief_state') or 'active'}",
                                "content": entity,
                                "metadata": {
                                    "source": "temporal_kg",
                                    "entity_type": entity.get("entity_type"),
                                    "confidence": entity.get("confidence"),
                                    "belief_state": entity.get("belief_state"),
                                    "owner_user_id": user_id,
                                },
                            },
                        )
        except Exception:
            pass
        return None

    async def _resolve_skill(self, workspace_id: str, skill_id: str) -> GraphNode | None:
        home = get_keprix_home()
        skills_root = home / "skills"
        if not skills_root.is_dir():
            return None
        for path in skills_root.rglob("SKILL.md"):
            parent = path.parent.name
            if parent == skill_id or path.parent.as_posix().endswith(skill_id):
                text = path.read_text(encoding="utf-8", errors="ignore")
                first = next((line.strip("# ").strip() for line in text.splitlines() if line.strip()), skill_id)
                return self._from_record(
                    "skill",
                    skill_id,
                    {"title": first, "summary": first, "content": {"path": str(path)}, "metadata": {"source": "skills"}},
                )
        return None

    async def _resolve_document(self, workspace_id: str, doc_id: str) -> GraphNode | None:
        home = get_keprix_home()
        for root_name in ("documents", "deliverables", "vault"):
            root = home / root_name
            if not root.exists():
                continue
            matches = list(root.rglob(doc_id))[:1] + list(root.rglob(f"{doc_id}.*"))[:1]
            for path in matches:
                if path.is_file():
                    return self._from_record(
                        "document",
                        doc_id,
                        {"title": path.name, "summary": path.name, "content": {"path": str(path)}},
                    )
        return None

    async def _resolve_source(self, workspace_id: str, source_id: str) -> GraphNode | None:
        row = self._data_plane_row(workspace_id, "research_sources", "source_id", source_id)
        if not row:
            row = self._data_plane_row(workspace_id, "research_sources", "id", source_id)
        if not row:
            return None
        title = str(row.get("title") or row.get("url") or source_id)
        return self._from_record("source", source_id, {"title": title, "summary": title, "content": row})

    async def _resolve_task(self, workspace_id: str, task_id: str) -> GraphNode | None:
        home = get_keprix_home()
        for path in (home / "tasks").glob("*.json") if (home / "tasks").is_dir() else []:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if str(data.get("id") or path.stem) != task_id:
                continue
            title = str(data.get("title") or data.get("name") or task_id)
            return self._from_record(
                "task",
                task_id,
                {
                    "title": title,
                    "summary": str(data.get("description") or title),
                    "metadata": {"status": data.get("status")},
                    "content": data,
                },
            )
        return None

    def _vault_conversation(self, session_id: str) -> GraphNode | None:
        root = get_keprix_home() / "vault" / "conversations"
        if not root.is_dir():
            return None
        matches = list(root.rglob(f"{session_id}.md"))
        if not matches:
            return None
        path = matches[0]
        text = path.read_text(encoding="utf-8", errors="ignore")
        meta, body = self._parse_simple_frontmatter(text)
        title = str(meta.get("title") or path.stem)
        preview = _short(body.replace("#", " "), 200) or title
        return self._from_record(
            "session",
            session_id,
            {
                "title": title,
                "summary": preview,
                "created_at": meta.get("captured_at"),
                "metadata": {
                    "source": "vault",
                    "message_count": meta.get("message_count"),
                    "path": str(path),
                },
                "content": {"id": session_id, "title": title, "path": str(path), "frontmatter": meta},
            },
        )

    @staticmethod
    def _parse_simple_frontmatter(text: str) -> tuple[dict[str, Any], str]:
        """Parse YAML-ish frontmatter without importing research_workspace (Py3.10-safe)."""
        if not text.startswith("---"):
            return {}, text
        end = text.find("\n---", 3)
        if end < 0:
            return {}, text
        raw = text[3:end].strip("\n")
        body = text[end + 4 :].lstrip("\n")
        meta: dict[str, Any] = {}
        for line in raw.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                meta[key] = value
        return meta, body

    def _data_plane_session(self, workspace_id: str, session_id: str) -> dict[str, Any] | None:
        return self._data_plane_row(workspace_id, "sessions", "session_id", session_id)

    def _data_plane_row(
        self,
        workspace_id: str,
        table: str,
        id_column: str,
        node_id: str,
    ) -> dict[str, Any] | None:
        try:
            from keprix.data_architecture.data_plane import get_workspace_data_plane

            db = get_workspace_data_plane(workspace_id).root / "data_plane.sqlite"
            if not db.is_file():
                return None
            with sqlite3.connect(str(db)) as conn:
                conn.row_factory = sqlite3.Row
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if table not in tables:
                    return None
                cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
                if id_column not in cols:
                    return None
                if "workspace_id" in cols:
                    row = conn.execute(
                        f"SELECT * FROM {table} WHERE {id_column} = ? AND workspace_id = ? LIMIT 1",
                        (node_id, workspace_id),
                    ).fetchone()
                else:
                    row = conn.execute(
                        f"SELECT * FROM {table} WHERE {id_column} = ? LIMIT 1",
                        (node_id,),
                    ).fetchone()
                return dict(row) if row else None
        except Exception:
            return None

    def _from_record(self, kind: str, node_id: str, record: dict[str, Any]) -> GraphNode:
        text = str(
            record.get("content")
            or record.get("summary")
            or record.get("description")
            or record.get("title")
            or node_id
        )
        if isinstance(record.get("content"), dict):
            text = str(
                record.get("summary")
                or record.get("description")
                or record.get("title")
                or node_id
            )
        label = str(record.get("label") or record.get("title") or record.get("name") or _short(text, 60))
        created = _parse_dt(record.get("created_at")) or _now()
        updated = _parse_dt(record.get("updated_at"))
        content = record.get("content")
        if content is None:
            content = record
        elif not isinstance(content, dict):
            content = {"text": content}
        return GraphNode(
            id=node_id,
            kind=kind,
            label=_short(label, 80),
            summary=_short(text, 200),
            created_at=created,
            updated_at=updated,
            metadata=dict(record.get("metadata") or {}),
            deleted=False,
            content=content,
        )
