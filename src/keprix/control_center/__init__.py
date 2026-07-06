"""Self-hosted agent control center (Prompt 61)."""

from keprix.control_center.activity_feed import list_approvals, list_recent_artifacts, recent_activity
from keprix.control_center.agent_server_registry import list_servers, register_server
from keprix.control_center.automation_server import dispatch_automation, list_automations
from keprix.control_center.event_triggers import create_webhook_automation, trigger_from_webhook
from keprix.control_center.scheduled_runs import create_scheduled_automation, schedule_playbook_run
from keprix.control_center.run_queue import fail_run, list_queue
from keprix.control_center.workspace_sessions import create_session, list_sessions, update_session_status

__all__ = [
    "create_scheduled_automation",
    "create_session",
    "create_webhook_automation",
    "dispatch_automation",
    "fail_run",
    "list_approvals",
    "list_automations",
    "list_queue",
    "list_recent_artifacts",
    "list_servers",
    "list_sessions",
    "recent_activity",
    "register_server",
    "schedule_playbook_run",
    "trigger_from_webhook",
    "update_session_status",
]
__all__ = ["register_server", "list_servers", "create_session"]
