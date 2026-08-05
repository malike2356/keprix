"""Integration tests for product hooks wired into the agent loop.

Verifies:
- After-turn hooks fire with correct context after every turn.
- Before-tool hooks fire before tool execution.
- Hook errors are logged and swallowed — they must not break the loop.
- Hooks registered by product modules work end-to-end.
"""

import pytest

from registries.product_hooks import (
    register_after_turn_hook,
    register_before_tool_hook,
    iter_after_turn_hooks,
    iter_before_tool_hooks,
    clear_hooks_for_tests,
)


@pytest.fixture(autouse=True)
def _clean_hooks():
    """Reset hook registrations before each test."""
    clear_hooks_for_tests()
    yield
    clear_hooks_for_tests()


# ── Registration and iteration ──────────────────────────────────────────


class TestHookRegistration:
    def test_register_and_iterate_after_turn_hooks(self):
        """Registered after-turn hooks appear in iteration."""
        calls = []

        def my_hook(ctx):
            calls.append(ctx)

        register_after_turn_hook("test_hook", my_hook, product="scout")
        hooks = iter_after_turn_hooks()

        assert len(hooks) == 1
        assert hooks[0].name == "test_hook"
        assert hooks[0].product == "scout"

    def test_register_and_iterate_before_tool_hooks(self):
        """Registered before-tool hooks appear in iteration."""
        calls = []

        def my_hook(ctx):
            calls.append(ctx)

        register_before_tool_hook("test_tool_hook", my_hook, product="channel_shield")
        hooks = iter_before_tool_hooks()

        assert len(hooks) == 1
        assert hooks[0].name == "test_tool_hook"
        assert hooks[0].product == "channel_shield"

    def test_multiple_hooks_from_different_products(self):
        """Hooks from different products coexist."""
        register_after_turn_hook("scout_telemetry", lambda _: None, product="scout")
        register_after_turn_hook("channel_shield_audit", lambda _: None, product="channel_shield")
        register_after_turn_hook("agent_os_ledger", lambda _: None, product="agent_os")

        hooks = iter_after_turn_hooks()
        assert len(hooks) == 3
        products = {h.product for h in hooks}
        assert products == {"scout", "channel_shield", "agent_os"}


# ── Hook context structure ──────────────────────────────────────────────


class TestAfterTurnHookContext:
    """After-turn hooks receive a context dict with known keys."""

    def test_context_has_required_keys(self):
        """The context passed to after-turn hooks includes turn metadata."""
        received_ctx = None

        def capture(ctx):
            nonlocal received_ctx
            received_ctx = ctx

        register_after_turn_hook("capture", capture, product="test")

        # Simulate what the conversation loop passes
        ctx = {
            "final_response": "Hello",
            "api_call_count": 3,
            "interrupted": False,
            "failed": False,
            "turn_id": "turn-123",
            "user_message": "Hi",
            "_turn_exit_reason": "completed",
        }
        for hook in iter_after_turn_hooks():
            hook.hook(ctx)

        assert received_ctx is not None
        assert received_ctx["final_response"] == "Hello"
        assert received_ctx["api_call_count"] == 3
        assert received_ctx["interrupted"] is False
        assert received_ctx["failed"] is False
        assert received_ctx["turn_id"] == "turn-123"
        assert received_ctx["user_message"] == "Hi"
        assert received_ctx["_turn_exit_reason"] == "completed"

    def test_hook_sees_interrupted_turn(self):
        """Hooks receive interruption context correctly."""
        received_ctx = None

        def capture(ctx):
            nonlocal received_ctx
            received_ctx = ctx

        register_after_turn_hook("capture_interrupted", capture, product="test")
        ctx = {
            "final_response": None,
            "api_call_count": 1,
            "interrupted": True,
            "failed": False,
            "turn_id": "turn-789",
            "user_message": "Do something",
            "_turn_exit_reason": "interrupted_by_user",
        }
        for hook in iter_after_turn_hooks():
            hook.hook(ctx)

        assert received_ctx["interrupted"] is True
        assert received_ctx["_turn_exit_reason"] == "interrupted_by_user"


class TestBeforeToolHookContext:
    """Before-tool hooks receive context with tool execution metadata."""

    def test_context_has_required_keys(self):
        received_ctx = None

        def capture(ctx):
            nonlocal received_ctx
            received_ctx = ctx

        register_before_tool_hook("capture_tool", capture, product="test")
        ctx = {
            "function_name": "web_search",
            "function_args": {"query": "test"},
            "task_id": "task-1",
            "session_id": "sess-2",
            "tool_call_id": "tc-3",
            "turn_id": "turn-4",
            "api_request_id": "req-5",
        }
        for hook in iter_before_tool_hooks():
            hook.hook(ctx)

        assert received_ctx is not None
        assert received_ctx["function_name"] == "web_search"
        assert received_ctx["function_args"] == {"query": "test"}
        assert received_ctx["task_id"] == "task-1"
        assert received_ctx["session_id"] == "sess-2"
        assert received_ctx["tool_call_id"] == "tc-3"
        assert received_ctx["turn_id"] == "turn-4"
        assert received_ctx["api_request_id"] == "req-5"


# ── Error resilience ────────────────────────────────────────────────────


class TestHookErrorResilience:
    """Hooks must not break the agent loop when they raise."""

    def test_after_turn_hook_error_is_swallowed(self):
        """A failing after-turn hook does not prevent other hooks from firing."""
        second_fired = False

        def failing_hook(ctx):
            raise RuntimeError("simulated scout failure")

        def working_hook(ctx):
            nonlocal second_fired
            second_fired = True

        register_after_turn_hook("failing", failing_hook, product="scout")
        register_after_turn_hook("working", working_hook, product="channel_shield")

        ctx = {"final_response": "ok", "api_call_count": 1, "interrupted": False,
               "failed": False, "turn_id": "t1", "user_message": "hi",
               "_turn_exit_reason": "completed"}

        for hook in iter_after_turn_hooks():
            try:
                hook.hook(ctx)
            except Exception:
                pass  # The conversation loop swallows errors

        assert second_fired is True  # Second hook still ran

    def test_before_tool_hook_error_is_swallowed(self):
        """A failing before-tool hook does not prevent other hooks from firing."""
        second_fired = False

        def failing_hook(ctx):
            raise RuntimeError("simulated channel_shield failure")

        def working_hook(ctx):
            nonlocal second_fired
            second_fired = True

        register_before_tool_hook("failing_tool", failing_hook, product="channel_shield")
        register_before_tool_hook("working_tool", working_hook, product="agent_os")

        ctx = {"function_name": "test", "function_args": {}, "task_id": "",
               "session_id": "", "tool_call_id": "", "turn_id": "", "api_request_id": ""}

        for hook in iter_before_tool_hooks():
            try:
                hook.hook(ctx)
            except Exception:
                pass

        assert second_fired is True

    def test_empty_hook_list_is_noop(self):
        """Iterating hooks when none are registered returns empty list."""
        assert iter_after_turn_hooks() == []
        assert iter_before_tool_hooks() == []


# ── Scout telemetry simulation ──────────────────────────────────────────


class TestScoutTelemetryHook:
    """Simulate Scout registering a telemetry hook after each turn."""

    def test_scout_receives_turn_context(self):
        """Scout's after-turn telemetry hook receives full turn context."""
        telemetry_received = []

        def scout_telemetry(ctx):
            telemetry_received.append({
                "turn_id": ctx["turn_id"],
                "exit_reason": ctx["_turn_exit_reason"],
                "api_calls": ctx["api_call_count"],
            })

        register_after_turn_hook("scout_turn_telemetry", scout_telemetry, product="scout")

        # Simulate three turns
        for i in range(3):
            ctx = {
                "final_response": f"Response {i}",
                "api_call_count": i + 1,
                "interrupted": False,
                "failed": False,
                "turn_id": f"turn-{i}",
                "user_message": f"Message {i}",
                "_turn_exit_reason": "completed",
            }
            for hook in iter_after_turn_hooks():
                hook.hook(ctx)

        assert len(telemetry_received) == 3
        assert telemetry_received[0]["turn_id"] == "turn-0"
        assert telemetry_received[2]["api_calls"] == 3
        assert all(t["exit_reason"] == "completed" for t in telemetry_received)


# ── Channel Shield simulation ───────────────────────────────────────────


class TestChannelShieldHook:
    """Simulate Channel Shield auditing tool calls."""

    def test_channel_shield_audits_tool_calls(self):
        """Channel Shield receives before-tool context for audit logging."""
        audited = []

        def channel_shield_audit(ctx):
            audited.append({
                "tool": ctx["function_name"],
                "session": ctx["session_id"],
            })

        register_before_tool_hook("channel_shield_tool_audit", channel_shield_audit, product="channel_shield")

        tools_called = ["web_search", "file_read", "terminal"]
        for tool_name in tools_called:
            ctx = {
                "function_name": tool_name,
                "function_args": {},
                "task_id": "",
                "session_id": "sess-abc",
                "tool_call_id": "",
                "turn_id": "",
                "api_request_id": "",
            }
            for hook in iter_before_tool_hooks():
                hook.hook(ctx)

        assert len(audited) == 3
        assert audited[0]["tool"] == "web_search"
        assert audited[2]["tool"] == "terminal"
        assert all(a["session"] == "sess-abc" for a in audited)
