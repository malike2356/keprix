"""System design and Architecture Decision Record workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix.playbook.runtime.graph import END, PlaybookGraph
from keprix.playbook.runtime.runner import PlaybookRunner
from keprix.personas.forge.persona import FORGE_PERSONA


@dataclass(slots=True)
class ArchitectureDecision:
    title: str
    context: str
    decision: str
    status: str = "proposed"
    positive_consequences: str = ""
    negative_consequences: str = ""
    alternatives: str = ""
    implementation_notes: str = ""
    adr_id: str = field(default_factory=lambda: str(uuid4())[:8])

    def to_dict(self) -> dict[str, Any]:
        return {
            "adr_id": self.adr_id,
            "title": self.title,
            "status": self.status,
            "context": self.context,
            "decision": self.decision,
            "positive_consequences": self.positive_consequences,
            "negative_consequences": self.negative_consequences,
            "alternatives": self.alternatives,
            "implementation_notes": self.implementation_notes,
            "date": datetime.now(UTC).date().isoformat(),
        }


class ForgeArchitect:
    def __init__(self, *, workspace_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.persona = FORGE_PERSONA
        self._template_path = Path(__file__).resolve().parent / "prompts" / "architecture.md"

    def render_adr(self, decision: ArchitectureDecision) -> str:
        template = self._template_path.read_text(encoding="utf-8")
        data = decision.to_dict()
        replacements = {
            "{{adr_id}}": data["adr_id"],
            "{{title}}": data["title"],
            "{{status}}": data["status"],
            "{{date}}": data["date"],
            "{{context}}": data["context"],
            "{{decision}}": data["decision"],
            "{{positive_consequences}}": data["positive_consequences"] or "- None noted",
            "{{negative_consequences}}": data["negative_consequences"] or "- None noted",
            "{{alternatives}}": data["alternatives"] or "- None documented",
            "{{implementation_notes}}": data["implementation_notes"] or "- TBD",
        }
        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)
        return rendered

    def build_adr_playbook(self) -> PlaybookGraph:
        graph = PlaybookGraph("forge-adr")

        async def draft_node(state: dict[str, Any]) -> dict[str, Any]:
            decision_data = dict(state.get("adr_input", {}))
            decision_data.pop("date", None)
            decision = ArchitectureDecision(**decision_data) if decision_data else ArchitectureDecision(
                title="Untitled",
                context="",
                decision="",
            )
            state["adr_draft"] = decision.to_dict()
            return state

        async def review_node(state: dict[str, Any]) -> dict[str, Any]:
            draft = state.get("adr_draft", {})
            if not draft.get("decision"):
                state["adr_review"] = {"approved": False, "reason": "decision text required"}
            else:
                state["adr_review"] = {"approved": True, "reason": "decision documented"}
            return state

        async def publish_node(state: dict[str, Any]) -> dict[str, Any]:
            draft = state.get("adr_draft", {})
            decision = ArchitectureDecision(
                adr_id=draft.get("adr_id", str(uuid4())[:8]),
                title=draft.get("title", "Untitled"),
                context=draft.get("context", ""),
                decision=draft.get("decision", ""),
                status=draft.get("status", "accepted"),
                positive_consequences=draft.get("positive_consequences", ""),
                negative_consequences=draft.get("negative_consequences", ""),
                alternatives=draft.get("alternatives", ""),
                implementation_notes=draft.get("implementation_notes", ""),
            )
            markdown = self.render_adr(decision)
            records = list(state.get("adrs", []))
            records.append({**decision.to_dict(), "markdown": markdown})
            state["adrs"] = records
            state["adr_markdown"] = markdown
            return state

        graph.add_node("draft", draft_node)
        graph.add_node("review", review_node)
        graph.add_node("publish", publish_node)
        graph.add_edge("draft", "review")
        graph.add_edge("review", "publish")
        graph.add_edge("publish", END)
        return graph

    async def record_adr(self, decision: ArchitectureDecision) -> dict[str, Any]:
        graph = self.build_adr_playbook()
        runner = PlaybookRunner(graph.compile())
        initial_state = {
            "workspace_id": self.workspace_id,
            "adr_input": decision.to_dict(),
            "adrs": [],
        }
        run = await runner.execute_inline(initial_state)
        return {
            "status": run.status.value,
            "adr": run.state.get("adr_draft"),
            "markdown": run.state.get("adr_markdown", ""),
            "adrs": run.state.get("adrs", []),
            "playbook_state": run.state,
        }
