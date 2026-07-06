"""Task routing and delegation logic for NEXUS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from keprix.multiagent.group_chat import GroupChat, GroupChatPolicy
from keprix.multiagent.message import AgentMessage, MessageType
from keprix.multiagent.runtime import send_message
from keprix.personas.nexus.persona import NEXUS_PERSONA


@dataclass(slots=True)
class RoutingDecision:
    primary_agent: str
    matched_agents: list[str] = field(default_factory=list)
    handled_by_nexus: bool = False
    reason: str = ""
    confidence: float = 0.0

    def is_multi_domain(self) -> bool:
        return len(self.matched_agents) > 1 and not self.handled_by_nexus


ROUTING_KEYWORDS: dict[str, list[str]] = {
    "FORGE": [
        "code",
        "build",
        "deploy",
        "architecture",
        "refactor",
        "bug",
        "api",
        "docker",
        "infrastructure",
        "ci",
        "cd",
        "pipeline",
        "repository",
        "test",
    ],
    "WARDEN": [
        "security",
        "audit",
        "compliance",
        "privacy",
        "gdpr",
        "vulnerability",
        "penetration",
        "policy",
        "encrypt",
    ],
    "SAGE": [
        "research",
        "investigate",
        "market",
        "intelligence",
        "knowledge",
        "study",
        "sources",
        "literature",
    ],
    "BEACON": [
        "copy",
        "campaign",
        "brand",
        "marketing",
        "client",
        "deliverable",
        "creative",
        "messaging",
        "launch",
    ],
    "PRISM": [
        "seo",
        "social media",
        "content growth",
        "ranking",
        "keywords",
        "instagram",
        "linkedin",
        "twitter",
        "tiktok",
    ],
    "COMPASS": [
        "strategy",
        "planning",
        "roadmap",
        "decision",
        "market analysis",
        "prioritise",
        "prioritize",
        "okr",
        "vision",
    ],
    "EMBER": [
        "wellbeing",
        "wellness",
        "habit",
        "mindset",
        "burnout",
        "personal growth",
        "mental health",
        "stress",
    ],
    "CODEX": [
        "contract",
        "legal",
        "nda",
        "agreement",
        "clause",
        "liability",
        "terms of service",
        "privacy policy",
        "regulatory",
        "incorporation",
        "indemnity",
        "governing law",
    ],
    "SCOUT": [
        "governance",
        "policy",
        "kill switch",
        "audit",
        "compliance",
        "evidence pack",
        "governance",
        "policy violation",
        "engagement lock",
    ],
    "ECHO": [
        "receptionist",
        "phone call",
        "inbound call",
        "book appointment",
        "meeting booking",
        "voicemail",
        "caller",
        "front desk",
        "voice reception",
    ],
}

NEXUS_DIRECT_KEYWORDS = [
    "status",
    "progress",
    "milestone",
    "deadline",
    "blocker",
    "coordination",
    "overview",
    "dashboard",
    "project status",
    "overall progress",
]


class NexusOrchestrator:
    def __init__(self, *, workspace_id: str, run_id: str) -> None:
        self.workspace_id = workspace_id
        self.run_id = run_id
        self.persona = NEXUS_PERSONA

    def route(self, user_message: str) -> RoutingDecision:
        text = user_message.lower()

        if any(keyword in text for keyword in NEXUS_DIRECT_KEYWORDS):
            return RoutingDecision(
                primary_agent="NEXUS",
                matched_agents=["NEXUS"],
                handled_by_nexus=True,
                reason="Project status or coordination request",
                confidence=1.0,
            )

        scores: dict[str, int] = {}
        for agent, keywords in ROUTING_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[agent] = score

        if not scores:
            return RoutingDecision(
                primary_agent="NEXUS",
                matched_agents=["NEXUS"],
                handled_by_nexus=True,
                reason="Ambiguous request; NEXUS coordinates",
                confidence=0.5,
            )

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_score = ranked[0][1]
        matched = [agent for agent, score in ranked if score == top_score]

        if len(matched) > 1:
            return RoutingDecision(
                primary_agent="NEXUS",
                matched_agents=matched,
                handled_by_nexus=False,
                reason="Multi-domain request",
                confidence=top_score / max(len(ROUTING_KEYWORDS[matched[0]]), 1),
            )

        primary = matched[0]
        return RoutingDecision(
            primary_agent=primary,
            matched_agents=[primary],
            handled_by_nexus=False,
            reason=f"Matched {primary} domain keywords",
            confidence=top_score / max(len(ROUTING_KEYWORDS[primary]), 1),
        )

    async def delegate(self, decision: RoutingDecision, task: str) -> list[AgentMessage]:
        if decision.handled_by_nexus:
            return [
                await send_message(
                    AgentMessage(
                        sender="NEXUS",
                        recipient="NEXUS",
                        workspace_id=self.workspace_id,
                        run_id=self.run_id,
                        content=task,
                        message_type=MessageType.SYSTEM,
                        metadata={"routing": decision.reason},
                    )
                )
            ]

        messages: list[AgentMessage] = []
        for agent in decision.matched_agents:
            messages.append(
                await send_message(
                    AgentMessage(
                        sender="NEXUS",
                        recipient=agent,
                        workspace_id=self.workspace_id,
                        run_id=self.run_id,
                        content=task,
                        metadata={
                            "routing": decision.reason,
                            "confidence": decision.confidence,
                        },
                    )
                )
            )
        return messages

    async def coordinate_multi(self, decision: RoutingDecision, task: str) -> list[AgentMessage]:
        chat = GroupChat(
            participants=["NEXUS", *decision.matched_agents],
            supervisor="NEXUS",
            policy=GroupChatPolicy.SUPERVISOR_MODERATED,
            workspace_id=self.workspace_id,
            run_id=self.run_id,
        )
        return await chat.dispatch(task, metadata={"routing": decision.reason})

    def detect_blockers(self, project_state: dict[str, Any]) -> list[dict[str, Any]]:
        from keprix.personas.nexus.project_tracker import ProjectState

        state = ProjectState.from_playbook_state(project_state)
        return state.detect_blockers()

    def escalate(self, blockers: list[dict[str, Any]]) -> dict[str, Any]:
        if not blockers:
            return {"escalated": False, "blockers": []}

        options = [
            "Reassign the blocked milestone to another agent",
            "Extend the deadline and notify stakeholders",
            "Descope the blocked dependency and proceed",
        ]
        return {
            "escalated": True,
            "blockers": blockers,
            "message": f"{len(blockers)} blocker(s) require user attention.",
            "options": options,
        }
