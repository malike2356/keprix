"""Agent OS CLI command handlers."""

from __future__ import annotations

import asyncio
import json

from keprix.agent_os.maturity_audit_service import MaturityAuditService
from keprix.agent_os.connections_service import ConnectionsService


def cmd_agent_os(args) -> int:
    if args.agent_os_command == "hello":
        from keprix.agent_os.hello_world import run_hello_world

        result = asyncio.run(
            run_hello_world(name=args.name, capture=not bool(getattr(args, "no_capture", False)))
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1
    if args.agent_os_command == "playbook":
        from keprix.agent_os.token_playbook import playbook_markdown, playbook_status

        if getattr(args, "markdown", False):
            print(playbook_markdown())
            return 0
        print(json.dumps(playbook_status(), indent=2))
        return 0
    if args.agent_os_command == "guardrails":
        from keprix.agent_os.guardrails import backup_vault, guardrails_status

        command = getattr(args, "guardrails_command", None) or "status"
        if command == "backup-vault":
            print(json.dumps(backup_vault(reason="cli"), indent=2))
            return 0
        print(json.dumps(guardrails_status(), indent=2))
        return 0
    if args.agent_os_command == "milestones":
        from keprix.agent_os.milestones import build_milestones

        print(json.dumps(build_milestones(user_id=args.user_id), indent=2))
        return 0
    if args.agent_os_command == "workflow":
        return _dispatch_workflow(args)
    if args.agent_os_command == "maturity":
        service = MaturityAuditService()
        if args.maturity_command == "run":
            result = service.run(workspace_id=args.workspace_id, workspace_path=args.workspace_path)
            print(json.dumps(result.to_dict(), indent=2))
            return 0
        if args.maturity_command == "show":
            result = service.get(args.audit_id)
            if result is None:
                print(json.dumps({"error": "maturity audit not found"}))
                return 1
            print(json.dumps(result.to_dict(), indent=2))
            return 0
        if args.maturity_command == "list":
            print(json.dumps({"audits": [audit.to_dict() for audit in service.list(limit=args.limit)]}, indent=2))
            return 0
        if args.maturity_command == "export":
            print(json.dumps(service.export_to_level_up(args.audit_id), indent=2))
            return 0
    if args.agent_os_command == "connections":
        service = ConnectionsService()
        if args.connections_command == "init":
            print(json.dumps(service.init_template(workspace_id=args.workspace, workspace_path=args.workspace_path), indent=2))
            return 0
        if args.connections_command == "show":
            domains = service.load(workspace_id=args.workspace, workspace_path=args.workspace_path)
            print(json.dumps({"domains": [domain.to_dict() for domain in domains]}, indent=2))
            return 0
        if args.connections_command == "set":
            print(json.dumps(service.update_domain(args.domain, status=args.status, tools=args.tools, workspace_id=args.workspace, workspace_path=args.workspace_path), indent=2))
            return 0
    print(json.dumps({"error": "unknown agent-os command"}))
    return 2


def _dispatch_workflow(args) -> int:
    from keprix.agent_os.auto_skill_writer import write_skill_from_workflow
    from keprix.agent_os.workflow_kanban import enqueue_workflow_steps, list_workflow_boards
    from keprix.agent_os.workflows.content_series import generate_content_series
    from keprix.agent_os.workflows.crm_import import clean_crm_import
    from keprix.agent_os.workflows.memory_system import run_memory_system

    if args.workflow_command == "boards":
        print(json.dumps({"boards": list_workflow_boards(limit=args.limit)}, indent=2))
        return 0

    if args.workflow_command == "content-series":
        platforms = [p.strip() for p in str(args.platforms).split(",") if p.strip()]
        result = generate_content_series(
            topic=args.topic,
            audience_questions=args.questions,
            platforms=platforms,
        )
        if not args.no_kanban:
            result["kanban"] = enqueue_workflow_steps(
                workflow="content-series",
                title=result["topic"],
                steps=result.get("steps") or [],
            )
        result["auto_skill"] = write_skill_from_workflow(
            workflow="content-series",
            summary=f"Content series for {result['topic']}",
            procedure="\n".join(f"- {step['title']}" for step in result.get("steps") or []),
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") == "ok" else 1

    if args.workflow_command == "crm-import":
        csv_text = args.csv_text
        if args.csv_file:
            from pathlib import Path

            csv_text = Path(args.csv_file).expanduser().read_text(encoding="utf-8")
        result = clean_crm_import(csv_text=csv_text, target=args.target)
        if result.get("status") == "ok":
            result["auto_skill"] = write_skill_from_workflow(
                workflow="crm-import",
                summary=f"CRM import cleaner for {args.target}",
                procedure="Dedupe emails, normalize columns, validate, export clean CSV.",
            )
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") == "ok" else 1

    if args.workflow_command == "memory":
        from uuid import uuid4

        messages = None
        session_id = None
        if args.note:
            session_id = f"cli-memory-{uuid4().hex[:10]}"
            messages = [
                {"role": "user", "content": args.note},
                {"role": "assistant", "content": "Captured by memory-system workflow."},
            ]
        result = asyncio.run(run_memory_system(query=args.query, session_id=session_id, messages=messages))
        result["auto_skill"] = write_skill_from_workflow(
            workflow="memory-system",
            summary="Single-vault memory loop: capture, store, read, visualize",
            procedure="Ensure vault → capture note → search → return graph stats.",
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") == "ok" else 1

    if args.workflow_command == "video":
        from keprix.agent_os.workflows.video_agent import generate_video_package

        result = generate_video_package(topic=args.topic, audience=args.audience, length_minutes=args.minutes)
        result["auto_skill"] = write_skill_from_workflow(
            workflow="video-agent",
            summary=f"Video package for {result['topic']}",
            procedure="\n".join(f"- {step['title']}" for step in result.get("steps") or []),
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") == "ok" else 1

    if args.workflow_command == "seo":
        from keprix.agent_os.workflows.seo_agent import generate_seo_package

        result = generate_seo_package(
            keywords=args.keywords,
            website=args.website,
            title=args.title or None,
        )
        result["auto_skill"] = write_skill_from_workflow(
            workflow="seo-agent",
            summary=f"SEO package for {result['primary_keyword']}",
            procedure="\n".join(f"- {step['title']}" for step in result.get("steps") or []),
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") == "ok" else 1

    if args.workflow_command == "outreach":
        from keprix.agent_os.workflows.outreach_agent import generate_outreach_package

        channels = [c.strip() for c in str(args.channels).split(",") if c.strip()]
        result = generate_outreach_package(
            audience=args.audience,
            offer=args.offer,
            channels=channels,
            days=args.days,
        )
        result["auto_skill"] = write_skill_from_workflow(
            workflow="outreach-agent",
            summary=f"Outreach package for {result['audience']}",
            procedure="\n".join(f"- {step['title']}" for step in result.get("steps") or []),
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") == "ok" else 1

    if args.workflow_command == "onboarding-path":
        from keprix.agent_os.workflows.onboarding_path import generate_onboarding_path

        result = generate_onboarding_path(product=args.product, audience=args.audience)
        result["auto_skill"] = write_skill_from_workflow(
            workflow="onboarding-path",
            summary=f"Onboarding path for {result['product']}",
            procedure="\n".join(f"- {step['title']}" for step in result.get("steps") or []),
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") == "ok" else 1

    if args.workflow_command == "error-paste":
        from pathlib import Path

        from keprix.agent_os.workflows.error_paste import analyze_error_paste

        error_text = args.error
        if args.error_file:
            error_text = Path(args.error_file).expanduser().read_text(encoding="utf-8")
        result = analyze_error_paste(error_text=error_text, context=args.context)
        if result.get("status") == "ok":
            result["auto_skill"] = write_skill_from_workflow(
                workflow="error-paste",
                summary=f"Error paste loop: {result.get('classification')}",
                procedure="\n".join(f"- {step}" for step in result.get("plan") or []),
            )
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") == "ok" else 1

    print(json.dumps({"error": "unknown workflow command"}))
    return 2
