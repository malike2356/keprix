"""Governed group chat sessions for multi-agent coordination (Prompt 58)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import uuid4

from keprix.backend.multiagent.message import AgentMessage, MessageType
from keprix.backend.multiagent.runtime import send_message


class GroupChatPolicy(StrEnum):
    ROUND_ROBIN = "round_robin"
    SUPERVISOR_MODERATED = "supervisor_moderated"
    VOTE_DECIDE = "vote_decide"
    DEBATE_SUMMARIZE = "debate_summarize"
    HUMAN_REVIEW = "human_review"


class GroupChat:
    def __init__(
        self,
        *,
        participants: list[str],
        supervisor: str,
        policy: GroupChatPolicy,
        workspace_id: str,
        run_id: str | None = None,
    ) -> None:
        if supervisor not in participants:
            participants = [supervisor, *participants]
        self.participants = list(dict.fromkeys(participants))
        self.supervisor = supervisor
        self.policy = policy
        self.workspace_id = workspace_id
        self.run_id = run_id or str(uuid4())
        self._round_index = 0
        self._votes: dict[str, str] = {}
        self._debate_notes: list[str] = []
        self._awaiting_human = False

    async def dispatch(self, content: str, *, metadata: dict[str, Any] | None = None) -> list[AgentMessage]:
        """Fan out a coordination task to participants under the chosen policy."""
        meta = dict(metadata or {})
        meta["policy"] = self.policy.value
        messages: list[AgentMessage] = []

        if self.policy == GroupChatPolicy.HUMAN_REVIEW:
            self._awaiting_human = True
            messages.append(
                await send_message(
                    AgentMessage(
                        sender=self.supervisor,
                        recipient="human_reviewer",
                        workspace_id=self.workspace_id,
                        run_id=self.run_id,
                        content=f"Review required before action: {content}",
                        message_type=MessageType.APPROVAL,
                        metadata={**meta, "requires_human": True},
                    )
                )
            )
            return messages

        if self.policy == GroupChatPolicy.SUPERVISOR_MODERATED:
            messages.append(
                await send_message(
                    AgentMessage(
                        sender=self.supervisor,
                        recipient=self.supervisor,
                        workspace_id=self.workspace_id,
                        run_id=self.run_id,
                        content=f"Coordinating: {content}",
                        message_type=MessageType.SYSTEM,
                        metadata=meta,
                    )
                )
            )
            targets = [p for p in self.participants if p != self.supervisor]
        elif self.policy == GroupChatPolicy.VOTE_DECIDE:
            targets = [p for p in self.participants if p != self.supervisor]
            for agent in targets:
                vote = f"vote:{agent}"
                self._votes[agent] = vote
                messages.append(
                    await send_message(
                        AgentMessage(
                            sender=agent,
                            recipient=self.supervisor,
                            workspace_id=self.workspace_id,
                            run_id=self.run_id,
                            content=f"Vote on: {content}",
                            message_type=MessageType.AGENT,
                            metadata={**meta, "vote": vote},
                        )
                    )
                )
            messages.append(
                await send_message(
                    AgentMessage(
                        sender=self.supervisor,
                        recipient=self.supervisor,
                        workspace_id=self.workspace_id,
                        run_id=self.run_id,
                        content=f"Decision after vote: proceed with {content}",
                        message_type=MessageType.SYSTEM,
                        metadata={**meta, "votes": dict(self._votes)},
                    )
                )
            )
            return messages
        elif self.policy == GroupChatPolicy.DEBATE_SUMMARIZE:
            targets = [p for p in self.participants if p != self.supervisor]
            for agent in targets:
                note = f"{agent} perspective on {content}"
                self._debate_notes.append(note)
                messages.append(
                    await send_message(
                        AgentMessage(
                            sender=agent,
                            recipient=self.supervisor,
                            workspace_id=self.workspace_id,
                            run_id=self.run_id,
                            content=note,
                            message_type=MessageType.AGENT,
                            metadata=meta,
                        )
                    )
                )
            summary = "; ".join(self._debate_notes)
            messages.append(
                await send_message(
                    AgentMessage(
                        sender=self.supervisor,
                        recipient=self.supervisor,
                        workspace_id=self.workspace_id,
                        run_id=self.run_id,
                        content=f"Summary: {summary}",
                        message_type=MessageType.SYSTEM,
                        metadata={**meta, "debate_notes": list(self._debate_notes)},
                    )
                )
            )
            return messages
        else:
            targets = self.participants

        for agent in targets:
            if self.policy == GroupChatPolicy.ROUND_ROBIN:
                if agent != self.participants[self._round_index % len(self.participants)]:
                    continue
            messages.append(
                await send_message(
                    AgentMessage(
                        sender=self.supervisor,
                        recipient=agent,
                        workspace_id=self.workspace_id,
                        run_id=self.run_id,
                        content=content,
                        metadata=meta,
                    )
                )
            )

        if self.policy == GroupChatPolicy.ROUND_ROBIN:
            self._round_index += 1

        return messages

    async def approve_human_review(self, *, approved: bool, reviewer: str = "human_reviewer") -> AgentMessage:
        self._awaiting_human = False
        return await send_message(
            AgentMessage(
                sender=reviewer,
                recipient=self.supervisor,
                workspace_id=self.workspace_id,
                run_id=self.run_id,
                content="Approved" if approved else "Rejected",
                message_type=MessageType.APPROVAL,
                metadata={"approved": approved, "policy": self.policy.value},
            )
        )
