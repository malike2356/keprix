"""Agent OS CLI parser."""

from __future__ import annotations

from argparse import _SubParsersAction
from collections.abc import Callable


def build_agent_os_parser(subparsers: _SubParsersAction, *, cmd_agent_os: Callable) -> None:
    parser = subparsers.add_parser("agent-os", help="Agent OS utilities")
    sub = parser.add_subparsers(dest="agent_os_command", required=True)

    maturity = sub.add_parser("maturity", help="Run Four C's maturity audits")
    maturity_sub = maturity.add_subparsers(dest="maturity_command", required=True)
    run = maturity_sub.add_parser("run", help="Run a maturity audit")
    run.add_argument("--workspace-id", default="personal-os")
    run.add_argument("--workspace-path")
    run.set_defaults(func=cmd_agent_os)
    show = maturity_sub.add_parser("show", help="Show a maturity audit")
    show.add_argument("audit_id")
    show.set_defaults(func=cmd_agent_os)
    list_cmd = maturity_sub.add_parser("list", help="List maturity audits")
    list_cmd.add_argument("--limit", type=int, default=20)
    list_cmd.set_defaults(func=cmd_agent_os)
    export = maturity_sub.add_parser("export", help="Export audit JSON for level-up")
    export.add_argument("audit_id")
    export.add_argument("--to-level-up", action="store_true")
    export.set_defaults(func=cmd_agent_os)

    connections = sub.add_parser("connections", help="Manage the tier-1 connections matrix")
    connections_sub = connections.add_subparsers(dest="connections_command", required=True)
    init = connections_sub.add_parser("init", help="Write default connections.md")
    init.add_argument("--workspace", default="personal-os")
    init.add_argument("--workspace-path")
    init.set_defaults(func=cmd_agent_os)
    show_connections = connections_sub.add_parser("show", help="Show parsed connections")
    show_connections.add_argument("--workspace", default="personal-os")
    show_connections.add_argument("--workspace-path")
    show_connections.set_defaults(func=cmd_agent_os)
    set_domain = connections_sub.add_parser("set", help="Set a domain status")
    set_domain.add_argument("domain")
    set_domain.add_argument("--status", required=True)
    set_domain.add_argument("--tool", action="append", dest="tools")
    set_domain.add_argument("--workspace", default="personal-os")
    set_domain.add_argument("--workspace-path")
    set_domain.set_defaults(func=cmd_agent_os)

    hello = sub.add_parser("hello", help="Day-1 Hello World workflow (first result in minutes)")
    hello.add_argument("--name", default="world")
    hello.add_argument("--no-capture", action="store_true", help="Skip writing the vault note")
    hello.set_defaults(func=cmd_agent_os)

    workflow = sub.add_parser("workflow", help="Run Agent OS workflows (Phases 2-4)")
    workflow_sub = workflow.add_subparsers(dest="workflow_command", required=True)

    content = workflow_sub.add_parser("content-series", help="Content Series Generator")
    content.add_argument("--topic", required=True)
    content.add_argument("--questions", default="")
    content.add_argument("--platforms", default="linkedin,x,youtube,instagram,email")
    content.add_argument("--no-kanban", action="store_true")
    content.set_defaults(func=cmd_agent_os)

    crm = workflow_sub.add_parser("crm-import", help="CRM Import / Clean")
    crm.add_argument("--csv", dest="csv_text", default="")
    crm.add_argument("--csv-file", dest="csv_file", default="")
    crm.add_argument("--target", default="generic")
    crm.set_defaults(func=cmd_agent_os)

    memory = workflow_sub.add_parser("memory", help="Memory System loop")
    memory.add_argument("--query", default="")
    memory.add_argument("--note", default="")
    memory.set_defaults(func=cmd_agent_os)

    video = workflow_sub.add_parser("video", help="Video Agent")
    video.add_argument("--topic", required=True)
    video.add_argument("--audience", default="general")
    video.add_argument("--minutes", type=int, default=8)
    video.set_defaults(func=cmd_agent_os)

    seo = workflow_sub.add_parser("seo", help="SEO Agent")
    seo.add_argument("--keywords", required=True)
    seo.add_argument("--website", default="https://example.com")
    seo.add_argument("--title", default="")
    seo.set_defaults(func=cmd_agent_os)

    outreach = workflow_sub.add_parser("outreach", help="Outreach / Lead Agent")
    outreach.add_argument("--audience", required=True)
    outreach.add_argument("--offer", required=True)
    outreach.add_argument("--channels", default="linkedin,email,x")
    outreach.add_argument("--days", type=int, default=14)
    outreach.set_defaults(func=cmd_agent_os)

    onboarding = workflow_sub.add_parser("onboarding-path", help="Onboarding Path Builder")
    onboarding.add_argument("--product", required=True)
    onboarding.add_argument("--audience", default="new users")
    onboarding.set_defaults(func=cmd_agent_os)

    boards = workflow_sub.add_parser("boards", help="List workflow Kanban boards")
    boards.add_argument("--limit", type=int, default=20)
    boards.set_defaults(func=cmd_agent_os)

    error_paste = workflow_sub.add_parser("error-paste", help="Error paste loop")
    error_paste.add_argument("--error", default="", help="Error text (or use --error-file)")
    error_paste.add_argument("--error-file", default="", help="Path to a file containing the error")
    error_paste.add_argument("--context", default="")
    error_paste.set_defaults(func=cmd_agent_os)

    milestones = sub.add_parser("milestones", help="Day 1 / 7 / 30 onboarding wizard progress")
    milestones.add_argument("--user-id", default="cli")
    milestones.set_defaults(func=cmd_agent_os)

    playbook = sub.add_parser("playbook", help="Token minimization playbook (10 techniques)")
    playbook.add_argument("--markdown", action="store_true", help="Print markdown instead of JSON")
    playbook.set_defaults(func=cmd_agent_os)

    guardrails = sub.add_parser("guardrails", help="Show Agent OS guardrails status")
    guardrails_sub = guardrails.add_subparsers(dest="guardrails_command")
    guardrails.set_defaults(func=cmd_agent_os)
    guardrails_sub.add_parser("status", help="Show guardrails status").set_defaults(func=cmd_agent_os)
    backup = guardrails_sub.add_parser("backup-vault", help="Snapshot the markdown vault now")
    backup.set_defaults(func=cmd_agent_os)
