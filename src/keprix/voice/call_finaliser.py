"""Post-call finalisation for Aiva phone calls."""

from __future__ import annotations

from keprix.voice.call_store import VoiceCallRecord, VoiceCallStore


class CallFinaliser:
    def __init__(self, store: VoiceCallStore | None = None) -> None:
        self.store = store or VoiceCallStore()

    async def finalise(self, record: VoiceCallRecord) -> VoiceCallRecord:
        if record.ended_at is None:
            record.finish()
        if not record.summary:
            user_turns = [turn.text for turn in record.transcript if turn.role in {"caller", "user"}]
            last_need = user_turns[-1] if user_turns else "no caller request captured"
            outcome = "escalated" if record.escalated else "handled by Aiva"
            record.summary = f"{record.caller_name or record.caller_number} called about {last_need}. Outcome: {outcome}."
        if "send" in (record.summary or "").lower() and not record.tasks_created:
            record.tasks_created.append(f"task-{record.call_sid}-follow-up")
        await self.store.save(record)
        return record
