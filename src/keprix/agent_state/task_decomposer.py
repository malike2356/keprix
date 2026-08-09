"""Break large tasks into discrete chunks of five to seven steps."""

from __future__ import annotations

import re
from typing import Sequence

from keprix.agent_state.context_state import ContextStateStore
from keprix.agent_state.models import ProjectState, StepRecord, TaskChunk, utc_now_iso

MIN_STEPS_PER_CHUNK = 5
MAX_STEPS_PER_CHUNK = 7
DEFAULT_MAX_CHUNKS = 5


_NUMBERED = re.compile(
    r"^\s*(?:(?:\d+)[.)]\s+|[-*]\s+)(.+)$",
    re.MULTILINE,
)


def extract_steps_from_description(task_description: str) -> list[str]:
    """Pull numbered/bulleted steps, else synthesize a coarse plan."""
    text = (task_description or "").strip()
    if not text:
        return ["Clarify task goals", "Execute work", "Verify outcome"]

    found = [m.group(1).strip() for m in _NUMBERED.finditer(text) if m.group(1).strip()]
    if len(found) >= 2:
        return found

    parts = [p.strip() for p in re.split(r"[;\n]+", text) if p.strip()]
    if len(parts) >= MIN_STEPS_PER_CHUNK:
        return parts

    return [
        f"Scope and constraints for: {text[:120]}",
        "Inventory current artifacts and dependencies",
        "Design the approach and decision points",
        "Implement first vertical slice",
        "Implement remaining core pieces",
        "Add tests and validation",
        "Document outcomes and handoff notes",
    ]


def plan_chunk_sizes(
    total: int,
    *,
    min_size: int = MIN_STEPS_PER_CHUNK,
    max_size: int = MAX_STEPS_PER_CHUNK,
    max_chunks: int | None = DEFAULT_MAX_CHUNKS,
) -> list[int]:
    """Return chunk sizes preferring [min_size, max_size] balance.

    A 30-step plan with defaults yields five chunks of six.
    Steps are never dropped; if total exceeds max_chunks * max_size,
    additional chunks at max_size are allowed.
    """
    if total <= 0:
        return []
    if total <= max_size:
        return [total]

    if max_chunks is not None and total <= max_chunks * max_size:
        n_chunks = None
        for candidate in range((total + max_size - 1) // max_size, max_chunks + 1):
            size = (total + candidate - 1) // candidate
            if min_size <= size <= max_size:
                n_chunks = candidate
                break
        if n_chunks is None:
            n_chunks = min(max_chunks, (total + max_size - 1) // max_size)
    else:
        n_chunks = (total + max_size - 1) // max_size

    base = total // n_chunks
    rem = total % n_chunks
    sizes = [base + (1 if i < rem else 0) for i in range(n_chunks)]

    fixed: list[int] = []
    for size in sizes:
        while size > max_size:
            fixed.append(max_size)
            size -= max_size
        if size:
            fixed.append(size)
    return fixed


def decompose(
    task_description: str,
    *,
    steps: Sequence[str] | None = None,
    max_steps_per_chunk: int = MAX_STEPS_PER_CHUNK,
    min_steps_per_chunk: int = MIN_STEPS_PER_CHUNK,
    max_chunks: int | None = DEFAULT_MAX_CHUNKS,
    context_snapshot: dict | None = None,
) -> list[TaskChunk]:
    """Return ``TaskChunk`` list; large plans use 5-7 steps per chunk."""
    step_texts = [
        str(s).strip()
        for s in (steps or extract_steps_from_description(task_description))
        if str(s).strip()
    ]
    if not step_texts:
        step_texts = extract_steps_from_description(task_description)

    sizes = plan_chunk_sizes(
        len(step_texts),
        min_size=min_steps_per_chunk,
        max_size=max_steps_per_chunk,
        max_chunks=max_chunks,
    )
    chunks: list[TaskChunk] = []
    cursor = 0
    snapshot = dict(context_snapshot or {})
    for index, size in enumerate(sizes, start=1):
        piece = step_texts[cursor : cursor + size]
        cursor += size
        chunk_id = f"chunk-{index:02d}"
        prev = chunks[-1].id if chunks else None
        chunks.append(
            TaskChunk(
                id=chunk_id,
                description=f"Chunk {index}: {piece[0][:80]}" if piece else f"Chunk {index}",
                steps=list(piece),
                dependencies=[prev] if prev else [],
                context_snapshot=dict(snapshot),
                status="pending",
            )
        )
    return chunks


class TaskDecomposer:
    """Attach decomposition to a durable project state file."""

    def __init__(self, store: ContextStateStore | None = None) -> None:
        self.store = store or ContextStateStore()

    def decompose(
        self,
        session_id: str,
        *,
        max_steps_per_chunk: int = MAX_STEPS_PER_CHUNK,
        replace_pending: bool = True,
    ) -> ProjectState:
        state = self.store.require_state(session_id)
        if state.checkpoint.status == "awaiting_approval":
            raise RuntimeError(
                "Cannot decompose while a checkpoint awaits human approval"
            )

        source_steps = [s.description for s in state.pending]
        if not source_steps and not state.completed and not state.in_progress:
            source_steps = extract_steps_from_description(state.task_description)

        raw_chunks = decompose(
            state.task_description,
            steps=source_steps,
            max_steps_per_chunk=max_steps_per_chunk,
            context_snapshot=state.snapshot(),
        )

        pending: list[StepRecord] = []
        rebuilt: list[TaskChunk] = []
        step_counter = 1
        for chunk in raw_chunks:
            step_ids: list[str] = []
            for text in chunk.steps:
                step_id = f"step-{step_counter:03d}"
                step_counter += 1
                step_ids.append(step_id)
                pending.append(
                    StepRecord(
                        id=step_id,
                        description=text,
                        status="pending",
                        chunk_id=chunk.id,
                        updated_at=utc_now_iso(),
                    )
                )
            rebuilt.append(
                TaskChunk(
                    id=chunk.id,
                    description=chunk.description,
                    steps=step_ids,
                    dependencies=list(chunk.dependencies),
                    context_snapshot=dict(chunk.context_snapshot),
                    status="pending",
                )
            )

        state.chunks = rebuilt
        if replace_pending:
            state.pending = pending
        state.current_chunk_id = rebuilt[0].id if rebuilt else None
        return self.store.write_state(state)
