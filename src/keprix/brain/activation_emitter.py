"""Emit live brain graph activation signals."""

from __future__ import annotations

from datetime import datetime, timezone
from keprix.compat import StrEnum
from keprix.brain.activation_bus import activation_bus
from keprix.data_architecture.graph_edges import add_graph_edge


class ActivationEventType(StrEnum):
    MEMORY_RETRIEVED = "memory_retrieved"
    SKILL_SELECTED = "skill_selected"
    SKILL_FIRED = "skill_fired"
    TOOL_CALLED = "tool_called"
    DOCUMENT_SEARCHED = "document_searched"
    TASK_READ = "task_read"
    SESSION_LINKED = "session_linked"


class ActivationEmitter:
    async def emit(
        self,
        event_type: ActivationEventType | str,
        *,
        workspace_id: str,
        session_id: str,
        node_kind: str,
        node_id: str,
        relation: str | None = None,
        confidence: float | None = None,
    ) -> None:
        event_type_value = str(event_type.value if isinstance(event_type, ActivationEventType) else event_type)
        event = {
            "type": event_type_value,
            "workspace_id": workspace_id,
            "session_id": session_id,
            "node_kind": node_kind,
            "node_id": node_id,
            "relation": relation or event_type_value,
            "confidence": confidence,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        # SESSION_LINKED historically emitted session->session self-loops, which
        # pollute the brain graph with stub edges and [deleted] tombstones after
        # in-memory sessions are lost on restart. Skip self-edges; still publish.
        is_self_loop = node_kind == "session" and node_id == session_id
        if not is_self_loop:
            try:
                add_graph_edge(
                    workspace_id=workspace_id,
                    source_kind=node_kind,
                    source_id=node_id,
                    target_kind="session",
                    target_id=session_id,
                    relation=relation or event_type_value,
                    metadata={"activation_type": event_type_value, "confidence": confidence},
                )
            except Exception:
                pass
        await activation_bus.publish(workspace_id, event)


activation_emitter = ActivationEmitter()
