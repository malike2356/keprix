"""OpenAI Agents-style runtime: specs, handoffs, guardrails, realtime."""

from keprix.agents_runtime.agent_spec import AgentSpec
from keprix.agents_runtime.guardrail import GuardrailResult, run_guardrails
from keprix.agents_runtime.handoff import HandoffRecord, execute_handoff
from keprix.agents_runtime.run_context import RunContext

__all__ = [
    "AgentSpec",
    "GuardrailResult",
    "run_guardrails",
    "HandoffRecord",
    "execute_handoff",
    "RunContext",
]
