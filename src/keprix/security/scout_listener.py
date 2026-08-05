"""Keprix from Scout command listener via Redis pub/sub."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from keprix.governance.kill_relay import apply_kill_directive, resume_agent
from keprix.governance.policy_receiver import get_policy_registry
from keprix.security.scout_config import ScoutConfig
from keprix.security.scout_control import (
    block_session,
    lift_quarantine,
    quarantine_tool,
    set_egress_force_blocked,
    unblock_session,
)
from keprix.security.scout_types import ScoutCommand, ScoutCommandMessage

logger = logging.getLogger(__name__)

CommandHandler = Callable[[ScoutCommandMessage], Awaitable[None]]

BROADCAST_CHANNEL = "scout:control:broadcast"
INSTANCE_CHANNEL_PREFIX = "scout:control:instance:"


class ScoutListener:
    """Receives Scout operator commands and applies local enforcement."""

    def __init__(self, config: ScoutConfig) -> None:
        self._config = config
        self.agent_id = config.agent_id or "keprix:local"
        self.instance_channel = f"{INSTANCE_CHANNEL_PREFIX}{self.agent_id}"
        self._redis: Any = None
        self._listen_task: asyncio.Task[None] | None = None
        self._running = False
        self._handlers: dict[ScoutCommand, CommandHandler] = {}
        self._register_default_handlers()

    @property
    def enabled(self) -> bool:
        return bool(self._config.redis_url and self._config.api_key)

    async def start(self) -> None:
        if not self.enabled:
            return
        if self._listen_task is not None and not self._listen_task.done():
            return
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(self._config.redis_url)
            await self._redis.ping()
        except Exception:
            logger.warning("ScoutListener Redis unavailable; running without Scout control")
            self._redis = None
            return
        self._running = True
        self._listen_task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        self._running = False
        if self._listen_task is not None:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    async def handle_message(self, raw: str | bytes) -> dict[str, str] | None:
        """Process one command payload. Used by tests and the listen loop."""
        try:
            payload = json.loads(raw)
            cmd = ScoutCommandMessage.from_payload(payload)
        except Exception as exc:
            logger.warning("ScoutListener invalid command payload: %s", exc)
            return None
        if cmd.agent_id not in {"*", self.agent_id}:
            return None
        if not self._command_valid(cmd):
            return {"status": "expired"}
        await self._execute(cmd)
        return {"status": "executed", "command_id": cmd.command_id}

    def _command_valid(self, cmd: ScoutCommandMessage) -> bool:
        if not cmd.ttl_seconds or not cmd.issued_at:
            return True
        try:
            issued = datetime.fromisoformat(cmd.issued_at.replace("Z", "+00:00"))
            expires_at = issued.timestamp() + int(cmd.ttl_seconds)
            return time.time() <= expires_at
        except Exception:
            return True

    async def _listen(self) -> None:
        assert self._redis is not None
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(BROADCAST_CHANNEL, self.instance_channel)
        try:
            async for message in pubsub.listen():
                if not self._running:
                    break
                if message.get("type") != "message":
                    continue
                result = await self.handle_message(message["data"])
                if result and result.get("command_id"):
                    await self._ack(result["command_id"], result.get("status", "executed"))
        finally:
            await pubsub.unsubscribe(BROADCAST_CHANNEL, self.instance_channel)
            await pubsub.close()

    async def _execute(self, cmd: ScoutCommandMessage) -> None:
        handler = self._handlers.get(cmd.command)
        if handler is None:
            await self._ack(cmd.command_id, "unknown_command")
            return
        try:
            await handler(cmd)
            await self._ack(cmd.command_id, "executed")
        except Exception as exc:
            logger.exception("ScoutListener command %s failed", cmd.command.value)
            await self._ack(cmd.command_id, f"failed:{exc}")

    async def _ack(self, command_id: str, status: str) -> None:
        if self._redis is None or not command_id:
            return
        ack_channel = f"scout:control:ack:{command_id}"
        payload = json.dumps(
            {
                "command_id": command_id,
                "agent_id": self.agent_id,
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        )
        await self._redis.publish(ack_channel, payload)

    def _register_default_handlers(self) -> None:
        self._handlers = {
            ScoutCommand.SUSPEND: self._handle_suspend,
            ScoutCommand.RESUME: self._handle_resume,
            ScoutCommand.BLOCK_SESSION: self._handle_block_session,
            ScoutCommand.UNBLOCK_SESSION: self._handle_unblock_session,
            ScoutCommand.QUARANTINE_TOOL: self._handle_quarantine_tool,
            ScoutCommand.LIFT_QUARANTINE: self._handle_lift_quarantine,
            ScoutCommand.BLOCK_EGRESS: self._handle_block_egress,
            ScoutCommand.UNBLOCK_EGRESS: self._handle_unblock_egress,
            ScoutCommand.SET_RATE_LIMIT: self._handle_set_rate_limit,
            ScoutCommand.CLEAR_RATE_LIMIT: self._handle_clear_rate_limit,
            ScoutCommand.SET_TOOL_POLICY: self._handle_set_tool_policy,
            ScoutCommand.SET_SANDBOX_POLICY: self._handle_set_sandbox_policy,
            ScoutCommand.SHUTDOWN: self._handle_shutdown,
            ScoutCommand.ROLLBACK_TO_CHECKPOINT: self._handle_rollback_checkpoint,
        }

    async def _handle_suspend(self, cmd: ScoutCommandMessage) -> None:
        apply_kill_directive("stop_agent", cmd.params)

    async def _handle_resume(self, _cmd: ScoutCommandMessage) -> None:
        resume_agent()

    async def _handle_block_session(self, cmd: ScoutCommandMessage) -> None:
        session_id = str(cmd.session_id or cmd.params.get("session_id") or "").strip()
        if session_id:
            block_session(session_id)

    async def _handle_unblock_session(self, cmd: ScoutCommandMessage) -> None:
        session_id = str(cmd.session_id or cmd.params.get("session_id") or "").strip()
        if session_id:
            unblock_session(session_id)

    async def _handle_quarantine_tool(self, cmd: ScoutCommandMessage) -> None:
        tool_name = str(cmd.params.get("tool_name") or "").strip()
        if tool_name:
            quarantine_tool(tool_name)
            get_policy_registry().apply("tool_block", {"tool_name": tool_name})

    async def _handle_lift_quarantine(self, cmd: ScoutCommandMessage) -> None:
        tool_name = str(cmd.params.get("tool_name") or "").strip()
        if tool_name:
            lift_quarantine(tool_name)

    async def _handle_block_egress(self, _cmd: ScoutCommandMessage) -> None:
        set_egress_force_blocked(True)

    async def _handle_unblock_egress(self, _cmd: ScoutCommandMessage) -> None:
        set_egress_force_blocked(False)

    async def _handle_set_rate_limit(self, cmd: ScoutCommandMessage) -> None:
        get_policy_registry().apply("rate_limit", cmd.params)

    async def _handle_clear_rate_limit(self, _cmd: ScoutCommandMessage) -> None:
        get_policy_registry().clear_rate_limit()

    async def _handle_set_tool_policy(self, cmd: ScoutCommandMessage) -> None:
        product_id = str(cmd.params.get("product") or cmd.params.get("product_id") or self._config.product)
        policy = cmd.params.get("policy")
        if isinstance(policy, dict):
            from keprix.security.product_policy import apply_product_policy

            apply_product_policy(product_id, policy, updated_by=str(cmd.issued_by or "scout"))
            return
        blocked = cmd.params.get("blocked_tools") or cmd.params.get("tools") or []
        for tool_name in blocked:
            name = str(tool_name).strip()
            if name:
                get_policy_registry().apply("tool_block", {"tool_name": name})

    async def _handle_set_sandbox_policy(self, cmd: ScoutCommandMessage) -> None:
        product_id = str(cmd.params.get("product") or cmd.params.get("product_id") or self._config.product)
        policy = cmd.params.get("policy")
        if isinstance(policy, dict):
            from keprix.security.product_policy import apply_product_policy

            apply_product_policy(product_id, policy, updated_by=str(cmd.issued_by or "scout"))
            return
        sandbox = cmd.params.get("sandbox") or {}
        if sandbox:
            from keprix.security.product_policy import apply_product_policy

            apply_product_policy(
                product_id,
                {"sandbox": sandbox, "security_profile": cmd.params.get("security_profile", "standard")},
                updated_by=str(cmd.issued_by or "scout"),
            )

    async def _handle_shutdown(self, cmd: ScoutCommandMessage) -> None:
        apply_kill_directive("stop_agent", {"permanent": True, **cmd.params})

    async def _handle_rollback_checkpoint(self, cmd: ScoutCommandMessage) -> None:
        working_dir = str(
            cmd.params.get("working_dir")
            or cmd.params.get("workspace_root")
            or os.getcwd()
        )
        commit_hash = str(
            cmd.params.get("commit_hash")
            or cmd.params.get("checkpoint_id")
            or ""
        ).removeprefix("ckpt-")
        if not commit_hash:
            raise ValueError("rollback_to_checkpoint requires commit_hash or checkpoint_id")
        from tools.checkpoint_manager import CheckpointManager
        from keprix.security.hermes_features import emit_checkpoint_rollback

        mgr = CheckpointManager(enabled=True)
        result = mgr.restore(working_dir, commit_hash)
        emit_checkpoint_rollback(
            working_dir=working_dir,
            commit_hash=commit_hash,
            success=bool(result.get("success")),
            triggered_by="scout_command",
        )
        if not result.get("success"):
            raise RuntimeError(str(result.get("error") or "checkpoint rollback failed"))


_listener: ScoutListener | None = None


def get_scout_listener() -> ScoutListener:
    global _listener
    if _listener is None:
        from keprix.security.scout_config import resolve_scout_config

        _listener = ScoutListener(resolve_scout_config())
    return _listener


def reset_scout_listener() -> None:
    global _listener
    _listener = None
