"""AutoGen-style multi-agent messaging and studio (Prompt 58)."""

from keprix.backend.multiagent.agent_tool import AgentTool, AgentToolResult
from keprix.backend.multiagent.group_chat import GroupChat, GroupChatPolicy
from keprix.backend.multiagent.message import AgentMessage, MessageType
from keprix.backend.multiagent.registry import AgentRegistry, MultiAgentPlaybook, get_agent_registry
from keprix.backend.multiagent.runtime import clear_messages, get_messages, send_message
from keprix.backend.multiagent.stream import RunStream, get_run_stream
from keprix.backend.multiagent.workbench import McpWorkbench, get_mcp_workbench

__all__ = [
    "AgentMessage",
    "AgentRegistry",
    "AgentTool",
    "AgentToolResult",
    "GroupChat",
    "GroupChatPolicy",
    "McpWorkbench",
    "MessageType",
    "MultiAgentPlaybook",
    "RunStream",
    "clear_messages",
    "get_agent_registry",
    "get_mcp_workbench",
    "get_messages",
    "get_run_stream",
    "send_message",
]
