"""Channel Shield orchestration: ingest -> pipeline -> deliver | quarantine."""

from __future__ import annotations

from typing import Any

from keprix.channel_shield.adapters.registry import get_adapter
from keprix.channel_shield.config import load_channel_shield_config
from keprix.channel_shield.pipeline import run_pipeline
from keprix.channel_shield.safe_summary import generate_safe_summary
from keprix.channel_shield.scout_bridge import emit_shield_signal
from keprix.channel_shield.store import ChannelShieldStore, get_channel_shield_store
from keprix.channel_shield.types import (
    MessageStatus,
    PipelineReport,
    ShieldEnvelope,
    Verdict,
)


class ChannelShieldService:
    def __init__(self, store: ChannelShieldStore | None = None) -> None:
        self.store = store or get_channel_shield_store()

    async def process_envelope(
        self,
        user_id: str,
        envelope: ShieldEnvelope,
        *,
        raw_bytes: bytes | None = None,
        attachment_bytes: dict[str, bytes] | None = None,
        sandbox_runner: Any | None = None,
        deep_link_base: str | None = None,
    ) -> dict[str, Any]:
        cfg = load_channel_shield_config()
        if not cfg.adapter_enabled(envelope.channel):
            raise ValueError(f"adapter disabled: {envelope.channel}")

        message = await self.store.ingest_envelope(user_id, envelope, raw_bytes=raw_bytes)
        await self.store.update_message(message.id, status=MessageStatus.ANALYSING.value)
        emit_shield_signal(
            "channel_shield.accept",
            envelope,
            message_id=message.id,
        )

        report = run_pipeline(
            envelope,
            cfg=cfg,
            attachment_bytes=attachment_bytes or {},
            sandbox_runner=sandbox_runner,
            message_id=message.id,
            raw_evidence_ref=message.raw_evidence_ref
            or envelope.raw_storage_uri
            or (f"shield://raw/{message.raw_blob_id}" if message.raw_blob_id else ""),
        )
        await self.store.update_message(
            message.id,
            agent_safe_content=dict(report.agent_safe_content or {}),
            policy_label=report.policy_label,
            raw_evidence_ref=report.raw_evidence_ref,
            text_preview=(report.agent_safe_content or {}).get("text", "")[:240]
            or message.text_preview,
        )
        action = await self._apply_verdict(
            user_id,
            message.id,
            envelope,
            report,
            deep_link_base=deep_link_base,
        )
        return {
            "message": (await self.store.get_message(message.id)).to_dict(),  # type: ignore[union-attr]
            "report": report.to_dict(),
            "action": action,
            "agentSafeContent": report.agent_safe_content,
            "rawEvidenceRef": report.raw_evidence_ref,
        }

    async def _apply_verdict(
        self,
        user_id: str,
        message_id: str,
        envelope: ShieldEnvelope,
        report: PipelineReport,
        *,
        deep_link_base: str | None = None,
    ) -> dict[str, Any]:
        cfg = load_channel_shield_config()
        scout_id = emit_shield_signal(
            f"channel_shield.verdict.{report.verdict.value}",
            envelope,
            report=report,
            message_id=message_id,
        )
        scout_ids = [scout_id] if scout_id else []
        await self.store.update_message(
            message_id,
            verdict=report.verdict.value,
            report=report.to_dict(),
            scout_ids=scout_ids,
        )

        deliver = report.verdict == Verdict.CLEAN
        if report.verdict == Verdict.SUSPECT and cfg.auto_release_suspects:
            deliver = True
        if report.verdict == Verdict.ERROR and not cfg.fail_closed_default:
            deliver = True

        adapter = get_adapter(envelope.channel)
        if deliver:
            result = await adapter.deliver(envelope, message_id)
            await self.store.record_delivery(message_id, envelope.channel, result)
            await self.store.update_message(message_id, status=MessageStatus.DELIVERED.value)
            # keep policy label from report
            await self.store.update_message(
                message_id,
                policy_label=report.policy_label or "clean",
                agent_safe_content=dict(report.agent_safe_content or {}),
            )
            emit_shield_signal(
                "channel_shield.deliver",
                envelope,
                report=report,
                message_id=message_id,
            )
            return {"decision": "deliver", "result": result}

        deep = None
        if deep_link_base:
            deep = f"{deep_link_base.rstrip('/')}/channel-shield?message={message_id}"
        summary = generate_safe_summary(envelope, report, ui_deep_link=deep)
        await self.store.update_message(
            message_id,
            status=MessageStatus.QUARANTINED.value,
            safe_summary=summary,
            policy_label=report.policy_label,
            agent_safe_content=dict(report.agent_safe_content or {}),
        )
        notify = await adapter.notify_safe_summary(envelope, message_id, summary)
        await self.store.record_summary(message_id, envelope.channel, summary, notify)
        await adapter.suppress_original(envelope)
        emit_shield_signal(
            "channel_shield.quarantine",
            envelope,
            report=report,
            message_id=message_id,
            extra={"safe_summary": summary[:200]},
        )
        return {"decision": "quarantine", "summary": summary, "notify": notify}

    async def release_message(
        self, message_id: str, user_id: str, *, is_admin: bool = False
    ) -> dict[str, Any]:
        message = await self.store.get_message(message_id, user_id)
        if message is None:
            raise KeyError("message not found")
        if message.status == MessageStatus.DESTROYED.value:
            raise ValueError("message destroyed")
        if message.verdict == Verdict.MALICIOUS.value and not is_admin:
            raise PermissionError("malicious release requires admin")
        envelope = ShieldEnvelope.from_dict(message.envelope)
        adapter = get_adapter(envelope.channel)
        result = await adapter.deliver(envelope, message_id)
        await self.store.record_delivery(message_id, envelope.channel, result)
        from keprix.channel_shield.agent_safe import allowed_actions_for
        from keprix.channel_shield.types import PolicyLabel

        safe = dict(message.agent_safe_content or {})
        label = PolicyLabel.CLEAN
        safe["policyLabel"] = label.value
        safe["allowedActions"] = allowed_actions_for(label, released=True)
        safe["verdict"] = message.verdict
        await self.store.update_message(
            message_id,
            status=MessageStatus.RELEASED.value,
            policy_label=label.value,
            agent_safe_content=safe,
        )
        emit_shield_signal("channel_shield.release", envelope, message_id=message_id)
        await self.store.add_event(message_id, message.protection_id, "message.released", {})
        return {"released": True, "result": result}

    async def destroy_message(
        self, message_id: str, user_id: str, *, is_admin: bool = False
    ) -> dict[str, Any]:
        if not is_admin:
            raise PermissionError("destroy requires admin")
        ok = await self.store.destroy_message(message_id, user_id)
        if not ok:
            raise KeyError("message not found")
        message = await self.store.get_message(message_id, user_id)
        if message:
            envelope = ShieldEnvelope.from_dict(
                message.envelope if message.envelope.get("channel") else {
                    "channel": message.channel,
                    "protectionId": message.protection_id,
                    "externalMessageId": message.external_message_id,
                    "conversationId": message.conversation_id,
                    "from": message.from_addr,
                    "to": message.to_addrs,
                    "text": "",
                }
            )
            emit_shield_signal("channel_shield.destroy", envelope, message_id=message_id)
        return {"destroyed": True}


def get_channel_shield_service() -> ChannelShieldService:
    return ChannelShieldService()
