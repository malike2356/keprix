"""Studio playbook template catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from keprix.playbook.graph_catalog import PLAYBOOK_GRAPH_CATALOG
from keprix.playbook.studio_store import PlaybookStudioStore

FEATURED_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "aiva-deal-analyse",
        "title": "Aiva deal analysis",
        "description": "Analyze a property deal, branch on score, and request approval.",
        "yaml": {
            "id": "aiva_deal_analyse",
            "name": "Aiva deal analysis",
            "variables": [{"name": "property_url", "type": "string", "default": "", "description": "Deal source URL"}],
            "entry": "analyse_deal",
            "steps": [
                {"id": "analyse_deal", "type": "agent_task", "prompt": "Analyze {{ state.property_url }}", "tools": []},
                {"id": "score_gate", "type": "condition", "expression": "score > 65", "on_true": "approval", "on_false": "record"},
                {"id": "approval", "type": "human_approval", "message": "Approve deal report?", "risk": "high"},
                {"id": "record", "type": "agent_task", "prompt": "Record low score outcome", "tools": []},
            ],
            "edges": [
                {"from": "analyse_deal", "to": "score_gate"},
                {"from": "score_gate", "to": "approval", "when": "true"},
                {"from": "score_gate", "to": "record", "when": "false"},
            ],
        },
    },
    {
        "id": "daily-digest",
        "title": "Daily digest",
        "description": "Collect updates and send a daily summary.",
        "yaml": {
            "id": "daily_digest",
            "name": "Daily digest",
            "variables": [{"name": "topic", "type": "string", "default": "today", "description": "Digest topic"}],
            "entry": "summarize",
            "steps": [
                {"id": "summarize", "type": "agent_task", "prompt": "Summarize {{ state.topic }}", "tools": []},
                {"id": "send_digest", "type": "http", "url": "https://example.com/webhook", "method": "POST"},
            ],
            "edges": [{"from": "summarize", "to": "send_digest"}],
        },
    },
    {
        "id": "support-triage",
        "title": "Support triage",
        "description": "Classify a ticket and request approval for high-risk replies.",
        "yaml": {
            "id": "support_triage",
            "name": "Support triage",
            "variables": [{"name": "ticket", "type": "string", "default": "", "description": "Ticket text"}],
            "entry": "classify",
            "steps": [
                {"id": "classify", "type": "agent_task", "prompt": "Classify {{ state.ticket }}", "tools": []},
                {"id": "risk_gate", "type": "condition", "expression": "risk == 'high'", "on_true": "approval", "on_false": "draft"},
                {"id": "approval", "type": "human_approval", "message": "Approve support reply?", "risk": "medium"},
                {"id": "draft", "type": "agent_task", "prompt": "Draft reply", "tools": []},
            ],
            "edges": [
                {"from": "classify", "to": "risk_gate"},
                {"from": "risk_gate", "to": "approval", "when": "true"},
                {"from": "risk_gate", "to": "draft", "when": "false"},
            ],
        },
    },
    {
        "id": "inbound-channel-shield",
        "title": "Inbound Channel Shield",
        "description": "Set up Channel Shield for a chosen channel, verify adapter health, and run a fixture E2E.",
        "yaml": {
            "id": "inbound_channel_shield",
            "name": "Inbound Channel Shield",
            "variables": [
                {
                    "name": "channel",
                    "type": "string",
                    "default": "email",
                    "description": "email|slack|teams|telegram|whatsapp|discord|sms|web",
                }
            ],
            "entry": "choose_channel",
            "steps": [
                {
                    "id": "choose_channel",
                    "type": "agent_task",
                    "prompt": "Confirm Channel Shield setup for {{ state.channel }} and collect protection key.",
                    "tools": [],
                },
                {
                    "id": "setup_email",
                    "type": "agent_task",
                    "prompt": "If channel is email: document MX/subdomain or shadow mailbox, TLS SMTP receiver, SPF/DKIM/DMARC checks.",
                    "tools": [],
                },
                {
                    "id": "setup_slack",
                    "type": "agent_task",
                    "prompt": "If channel is slack: Events API signing secret, team_id protection key, file download before analysis, intercept-bot honesty.",
                    "tools": [],
                },
                {
                    "id": "setup_teams",
                    "type": "agent_task",
                    "prompt": "If channel is teams: Bot Framework / Graph admin consent, tenant_id key, attachment download.",
                    "tools": [],
                },
                {
                    "id": "setup_messaging",
                    "type": "agent_task",
                    "prompt": "If channel is telegram/whatsapp/discord/sms/web: collect bot/WABA/guild/number/embed key; media to immutable store; safe summary constraints.",
                    "tools": [],
                },
                {
                    "id": "create_protection",
                    "type": "agent_task",
                    "prompt": "Create protection via /api/channel-shield/protections for {{ state.channel }}.",
                    "tools": [],
                },
                {
                    "id": "verify_adapter",
                    "type": "agent_task",
                    "prompt": "Run adapter verify/health for {{ state.channel }}.",
                    "tools": [],
                },
                {
                    "id": "agent_os_check",
                    "type": "agent_task",
                    "prompt": "Confirm Agent OS ingress guard and employee action drawer are available for this protection.",
                    "tools": [],
                },
                {
                    "id": "e2e_gate",
                    "type": "condition",
                    "expression": "e2e_ok == true",
                    "on_true": "done",
                    "on_false": "approval",
                },
                {
                    "id": "approval",
                    "type": "human_approval",
                    "message": "E2E failed or partial. Approve going live anyway?",
                    "risk": "high",
                },
                {
                    "id": "done",
                    "type": "agent_task",
                    "prompt": "Record Channel Shield ready for {{ state.channel }}.",
                    "tools": [],
                },
            ],
            "edges": [
                {"from": "choose_channel", "to": "setup_email"},
                {"from": "setup_email", "to": "setup_slack"},
                {"from": "setup_slack", "to": "setup_teams"},
                {"from": "setup_teams", "to": "setup_messaging"},
                {"from": "setup_messaging", "to": "create_protection"},
                {"from": "create_protection", "to": "verify_adapter"},
                {"from": "verify_adapter", "to": "agent_os_check"},
                {"from": "agent_os_check", "to": "e2e_gate"},
                {"from": "e2e_gate", "to": "done", "when": "true"},
                {"from": "e2e_gate", "to": "approval", "when": "false"},
            ],
        },
    },
]


def list_templates(*, include_custom: bool = True) -> list[dict[str, Any]]:
    templates: list[dict[str, Any]] = []
    for item in PLAYBOOK_GRAPH_CATALOG:
        templates.append(
            {
                "id": item["graph_id"],
                "title": item["title"],
                "description": item["description"],
                "source": "graph_catalog",
                "yaml": {
                    "id": item["graph_id"].replace("-", "_"),
                    "name": item["title"],
                    "entry": item.get("entry"),
                    "steps": item.get("steps") or [],
                    "edges": item.get("edges") or [],
                },
            }
        )
    templates.extend({**item, "source": "featured"} for item in FEATURED_TEMPLATES)
    if include_custom:
        template_dir = _template_dir()
        if template_dir.exists():
            for path in sorted(template_dir.glob("*.yaml")):
                parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                templates.append(
                    {
                        "id": path.stem,
                        "title": str(parsed.get("name") or path.stem),
                        "description": str(parsed.get("description") or "Custom template"),
                        "source": "custom",
                        "yaml": parsed,
                    }
                )
    return templates


def get_template(template_id: str) -> dict[str, Any] | None:
    for template in list_templates():
        if template["id"] == template_id:
            return template
    return None


def save_as_template(playbook_id: str, *, title: str, description: str) -> str:
    yaml_doc, _layout = PlaybookStudioStore().load(playbook_id)
    template_id = title.lower().replace(" ", "_").replace("-", "_")
    yaml_doc = {**yaml_doc, "name": title, "description": description}
    directory = _template_dir()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{template_id}.yaml").write_text(yaml.safe_dump(yaml_doc, sort_keys=False), encoding="utf-8")
    return template_id


def _template_dir() -> Path:
    return Path.home() / ".keprix" / "playbooks" / "templates"
