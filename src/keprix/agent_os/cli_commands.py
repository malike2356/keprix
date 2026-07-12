"""CLI: `keprix agent-os audit ...`"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def register_cli(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="agent_os_command", required=True)
    audit = sub.add_parser("audit", help="Workflow audit commands")
    audit_sub = audit.add_subparsers(dest="audit_command", required=True)

    start = audit_sub.add_parser("start", help="Start a workflow audit")
    start.add_argument("--mode", choices=["manual", "session-scan", "session_scan", "interview"], required=True)
    start.add_argument("--sessions", type=int, default=10)

    audit_sub.add_parser("list", help="List workflow audits")
    show = audit_sub.add_parser("show", help="Show one audit")
    show.add_argument("audit_id")

    export = audit_sub.add_parser("export", help="Export audit skill proposals")
    export.add_argument("audit_id")
    export.add_argument("--to-proposals", action="store_true")
    import_seed = audit_sub.add_parser("import", help="Import an audit seed")
    import_seed.add_argument("--seed", required=True)

    promote = sub.add_parser("promote", help="Promote a skill to an automation")
    promote.add_argument("--skill", required=True)
    promote.add_argument("--to", choices=["cron", "playbook", "agent-app", "agent_app"], required=True)
    promote.add_argument("--schedule", default=None)
    promote.add_argument("--name", default=None)
    promote.add_argument("--deliver-to", default=None)

    links = sub.add_parser("links", help="List promoted automation links")
    links.add_argument("--skill", default=None)

    audit.set_defaults(func=_dispatch_audit)
    promote.set_defaults(func=_dispatch_promote)
    links.set_defaults(func=_dispatch_links)


def _cli_user() -> dict[str, Any]:
    return {"id": "cli", "user_id": "cli", "username": "cli"}


def _dispatch_audit(args: argparse.Namespace) -> int:
    from keprix.agent_os.workflow_audit_service import WorkflowAuditService

    service = WorkflowAuditService()
    user = _cli_user()
    if args.audit_command == "start":
        audit = service.start(args.mode, user, session_count=args.sessions)
        print(json.dumps(audit.to_dict(), indent=2))
        return 0
    if args.audit_command == "list":
        audits = service.list_audits(user)
        print(json.dumps([audit.to_dict() for audit in audits], indent=2))
        return 0
    if args.audit_command == "show":
        audit = service.get(args.audit_id)
        if audit is None:
            print(f"audit not found: {args.audit_id}", file=sys.stderr)
            return 1
        print(json.dumps(audit.to_dict(), indent=2))
        return 0
    if args.audit_command == "export":
        if not args.to_proposals:
            print("--to-proposals is required", file=sys.stderr)
            return 2
        try:
            count = service.export_to_proposals(args.audit_id)
        except KeyError:
            print(f"audit not found: {args.audit_id}", file=sys.stderr)
            return 1
        print(json.dumps({"exported": count}))
        return 0
    if args.audit_command == "import":
        from keprix.agent_os.audit_seed_importer import import_audit_seed

        audit = import_audit_seed(args.seed, user_id="cli")
        print(json.dumps(audit.to_dict(), indent=2))
        return 0
    print("unknown audit command", file=sys.stderr)
    return 2


def _dispatch_promote(args: argparse.Namespace) -> int:
    from keprix.agent_os.automation_promoter import AutomationPromoter

    target = args.to.replace("-", "_")
    try:
        result = AutomationPromoter().promote(
            skill_slug=args.skill,
            target=target,
            schedule=args.schedule,
            name=args.name,
            deliver_to=args.deliver_to,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


def _dispatch_links(args: argparse.Namespace) -> int:
    from keprix.agent_os.automation_promoter import AutomationPromoter

    print(json.dumps(AutomationPromoter().links_for_skill(args.skill) if args.skill else [link.to_dict() for link in AutomationPromoter().links.list()], indent=2))
    return 0
