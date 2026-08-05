"""Bridge structured workspace files into episodic memory search."""

from __future__ import annotations

from pathlib import Path

from keprix.memory.episodic.store import EpisodicStore, create_episodic_store


def summarize_file(path: str | Path) -> str:
    path = Path(path)
    text = ""
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8")[:600]
        except UnicodeDecodeError:
            text = ""
    topic = path.stem.replace("-", " ").replace("_", " ").title()
    return f"Workspace file: {path.name}. Topic: {topic}. {text}".strip()


class MemoryIndexBridge:
    def __init__(self, store: EpisodicStore | None = None, user_id: str = "default") -> None:
        self.store = store or create_episodic_store()
        self.user_id = user_id

    async def link_file(self, file_path: str | Path, workspace_id: str | None = None) -> str:
        path = Path(file_path)
        return await self.store.save(
            self.user_id,
            summarize_file(path),
            metadata={
                "type": "workspace_file",
                "path": str(path),
                "workspace_id": workspace_id,
                "tags": ["workspace_file", path.suffix.lstrip(".")],
            },
        )

    async def recall_paths(self, query: str, limit: int = 10) -> list[str]:
        memories = await self.store.search(self.user_id, query, limit=limit)
        paths: list[str] = []
        for memory in memories:
            if memory.metadata.get("type") == "workspace_file" and memory.metadata.get("path"):
                paths.append(str(memory.metadata["path"]))
        return paths
