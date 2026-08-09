"""Built-in slash command handlers."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from keprix.config.constants import PRODUCT_NAME, PRODUCT_VERSION
from keprix.slash.registry import SlashRegistry
from keprix.slash.schemas import SlashCommand, SlashContext, SlashResult

_STARTED_AT = time.time()
_TOOL_ALLOWLIST = {
    name.strip().lower()
    for name in os.environ.get("KEPRIX_SLASH_TOOL_ALLOWLIST", "help,status,whoami").split(",")
    if name.strip()
}


async def _help(ctx: SlashContext) -> SlashResult:
    from keprix.slash.registry import get_slash_registry

    commands = get_slash_registry().list_for_role(ctx.role)
    lines = [f"Slash commands for role `{ctx.role}` on `{ctx.channel}`:"]
    for command in commands:
        lines.append(f"- `/{command.name}`: {command.description}")
    return SlashResult(ok=True, message="\n".join(lines))


async def _status(ctx: SlashContext) -> SlashResult:
    model = os.environ.get("KEPRIX_MODEL", "default")
    gateway = "running" if os.environ.get("KEPRIX_GATEWAY_RUNNING") == "1" else "unknown"
    memory = "memory-store" if os.environ.get("KEPRIX_USE_MEMORY_STORE") == "1" else "disabled"
    governance = (
        "enabled"
        if os.environ.get("KEPRIX_GOVERNANCE_ENABLED", "").lower() in {"1", "true", "yes"}
        else "disabled"
    )
    message = (
        f"{PRODUCT_NAME} {PRODUCT_VERSION}\n"
        f"Model: {model}\n"
        f"Gateway: {gateway}\n"
        f"Memory: {memory}\n"
        f"Governance: {governance}"
    )
    return SlashResult(ok=True, message=message)


async def _whoami(ctx: SlashContext) -> SlashResult:
    message = (
        f"user_id: {ctx.user_id}\n"
        f"workspace_id: {ctx.workspace_id}\n"
        f"role: {ctx.role}\n"
        f"channel: {ctx.channel}\n"
        f"channel_user_id: {ctx.channel_user_id}"
    )
    return SlashResult(ok=True, message=message, ephemeral=True)


async def _memory_search(ctx: SlashContext) -> SlashResult:
    query = " ".join(ctx.args).strip()
    if not query:
        return SlashResult(ok=False, message="Usage: /memory search <query>")
    try:
        from keprix.memory.episodic.store import create_episodic_store

        store = create_episodic_store()
        results = await store.search(ctx.user_id, query, limit=5)
        if not results:
            return SlashResult(ok=True, message="No memories found.")
        lines = [f"- {item.content}" for item in results[:5]]
        return SlashResult(ok=True, message="Memory results:\n" + "\n".join(lines))
    except Exception as exc:
        return SlashResult(ok=True, message=f"Memory search unavailable: {exc}")


async def _memory_save(ctx: SlashContext) -> SlashResult:
    text = " ".join(ctx.args).strip()
    if not text:
        return SlashResult(ok=False, message='Usage: /memory save "text to remember"')
    preview = f"Save memory for {ctx.user_id}:\n{text}"
    return SlashResult(
        ok=True,
        message=preview,
        requires_confirmation=True,
        data={"action": "memory.save", "content": text},
    )


async def _playbook_scan(ctx: SlashContext) -> SlashResult:
    from keprix.playbook.hwfit import scan_hardware

    hardware = scan_hardware()
    return SlashResult(ok=True, message="Hardware scan complete.", data={"hardware": hardware})


async def _playbook_models(ctx: SlashContext) -> SlashResult:
    from keprix.playbook.hwfit import rank_models, scan_hardware

    hardware = scan_hardware()
    models = rank_models(hardware)[:10]
    lines = [f"- {item['id']}: fit={item.get('fit_score', 0):.2f}" for item in models]
    return SlashResult(ok=True, message="Recommended local models:\n" + "\n".join(lines), data={"models": models})


async def _playbook_serve(ctx: SlashContext) -> SlashResult:
    model = " ".join(ctx.args).strip()
    if not model:
        return SlashResult(ok=False, message="Usage: /playbook serve <model>")
    preview = f"Start local model backend for `{model}`?"
    return SlashResult(
        ok=True,
        message=preview,
        requires_confirmation=True,
        data={"action": "playbook.serve", "model": model},
    )


async def _tools(ctx: SlashContext) -> SlashResult:
    try:
        from tools.registry import registry

        names = sorted(registry.get_all_tool_names())[:40]
        return SlashResult(ok=True, message="Enabled tools:\n" + "\n".join(f"- {name}" for name in names))
    except Exception:
        return SlashResult(ok=True, message="Enabled tools: registry unavailable in this runtime.")


async def _tool_run(ctx: SlashContext) -> SlashResult:
    if not ctx.args:
        return SlashResult(ok=False, message='Usage: /tool run <name> <json> or --json {"k":"v"}')
    tool_name = ctx.args[0].lower()
    payload: dict[str, Any] = ctx.json_args or {}
    if not payload and len(ctx.args) > 1:
        payload = json.loads(" ".join(ctx.args[1:]))
    allowlisted = tool_name in _TOOL_ALLOWLIST
    preview = f"Run tool `{tool_name}` with args {json.dumps(payload)}?"
    result = SlashResult(
        ok=True,
        message=preview,
        data={"action": "tool.run", "tool": tool_name, "args": payload},
    )
    if not allowlisted:
        result.requires_confirmation = True
    else:
        result.message = f"Tool `{tool_name}` is allowlisted; execution preview only."
    return result


async def _research(ctx: SlashContext) -> SlashResult:
    query = " ".join(ctx.args).strip()
    if not query:
        return SlashResult(ok=False, message='Usage: /research "query" [--depth deep]')
    depth = ctx.flags.get("depth", "standard")
    model = ctx.flags.get("model", "default")
    preview = f"Start research job?\nQuery: {query}\nDepth: {depth}\nModel: {model}"
    return SlashResult(
        ok=True,
        message=preview,
        requires_confirmation=True,
        data={"action": "research.start", "query": query, "depth": depth, "model": model},
    )


async def _settings(ctx: SlashContext) -> SlashResult:
    keys = sorted(os.environ.keys())
    visible = [key for key in keys if key.startswith("KEPRIX_")][:20]
    lines = [f"- {key}={os.environ.get(key, '')}" for key in visible]
    return SlashResult(ok=True, message="Editable settings summary:\n" + "\n".join(lines))


async def _settings_set(ctx: SlashContext) -> SlashResult:
    if len(ctx.args) < 2:
        return SlashResult(ok=False, message="Usage: /settings set <key> <value>")
    key, value = ctx.args[0], " ".join(ctx.args[1:])
    preview = f"Set `{key}` to `{value}`?"
    return SlashResult(
        ok=True,
        message=preview,
        requires_confirmation=True,
        data={"action": "settings.set", "key": key, "value": value},
    )


async def _channels(ctx: SlashContext) -> SlashResult:
    channels = ctx.metadata.get("channels") or ["webchat", "cli"]
    lines = [f"- {name}: ok" for name in channels]
    return SlashResult(ok=True, message="Connected channels:\n" + "\n".join(lines))


async def _governance_status(ctx: SlashContext) -> SlashResult:
    from keprix.governance.client import get_governance_client

    status = await get_governance_client().status()
    state = "connected" if status.get("connected") else "not connected"
    heartbeat = status.get("last_heartbeat_ok")
    hb_text = "ok" if heartbeat else "pending"
    message = (
        f"Governance provider: {state}\n"
        f"Instance: {status.get('instance_id') or 'n/a'}\n"
        f"Last heartbeat: {hb_text}"
    )
    return SlashResult(ok=True, message=message)


async def _opportunity(ctx: SlashContext) -> SlashResult:
    from keprix.opportunity.slash import execute_opportunity_slash, parse_opportunity_slash

    text = " ".join(ctx.args).strip()
    intent = parse_opportunity_slash(text)
    if intent.action == "help" and not text:
        intent = parse_opportunity_slash("help")
    if intent.needs_clarification:
        return SlashResult(ok=True, message=intent.clarification)
    result = await execute_opportunity_slash(
        intent,
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
    )
    requires_confirmation = intent.action == "prepare_launch" and not intent.dry_run
    return SlashResult(
        ok=True,
        message=result.summary,
        data=result.payload,
        requires_confirmation=requires_confirmation,
        risk_level="high" if requires_confirmation else "medium",
    )


async def _safety(ctx: SlashContext) -> SlashResult:
    message = (
        "Active safety rules:\n"
        "- Destructive slash commands require confirmation\n"
        "- Tool execution requires confirmation unless allowlisted\n"
        "- Cyber commands require active authorization\n"
        "- Secrets are redacted from audit logs"
    )
    return SlashResult(ok=True, message=message)


async def _diagnostics(ctx: SlashContext) -> SlashResult:
    uptime = int(time.time() - _STARTED_AT)
    message = (
        f"Version: {PRODUCT_VERSION}\n"
        f"Uptime: {uptime}s\n"
        f"Queue depth: {ctx.metadata.get('queue_depth', 0)}\n"
        f"Recent errors: {ctx.metadata.get('recent_errors', 0)}"
    )
    return SlashResult(ok=True, message=message)


async def _approve(ctx: SlashContext) -> SlashResult:
    token = ctx.args[0] if ctx.args else ctx.confirmation_token
    if not token:
        return SlashResult(ok=False, message="Usage: /approve <token>")
    from keprix.slash.executor import approve_token

    return await approve_token(ctx, token)


async def _cancel(ctx: SlashContext) -> SlashResult:
    token = ctx.args[0] if ctx.args else ctx.confirmation_token
    if not token:
        return SlashResult(ok=False, message="Usage: /cancel <token>")
    from keprix.slash.executor import cancel_token

    return await cancel_token(ctx, token)


async def _data_import(ctx: SlashContext) -> SlashResult:
    return SlashResult(
        ok=True,
        message="Use POST /api/data/import with a file upload, or import via the research dataset manager.",
    )


async def _data_export(ctx: SlashContext) -> SlashResult:
    dataset_id = ctx.args[0] if ctx.args else ""
    if not dataset_id:
        return SlashResult(ok=False, message="Usage: /data export <dataset_id>")
    from keprix.data_plane.catalog import get_dataset_catalog

    row = get_dataset_catalog().get(dataset_id)
    if row is None:
        return SlashResult(ok=False, message=f"Dataset not found: {dataset_id}")
    return SlashResult(
        ok=True,
        message=f"Export {dataset_id} via POST /api/data/export?dataset_id={dataset_id}&format={row.get('format', 'csv')}",
    )


async def _data_profile(ctx: SlashContext) -> SlashResult:
    dataset_id = ctx.args[0] if ctx.args else ""
    if not dataset_id:
        return SlashResult(ok=False, message="Usage: /data profile <dataset_id>")
    from keprix.data_plane.catalog import get_dataset_catalog

    row = get_dataset_catalog().get(dataset_id)
    if row is None:
        return SlashResult(ok=False, message=f"Dataset not found: {dataset_id}")
    return SlashResult(
        ok=True,
        message=f"Dataset {dataset_id}: {row.get('name')} ({row.get('format')}), rows={row.get('row_count')}",
    )


async def _jobs_list(ctx: SlashContext) -> SlashResult:
    from keprix.jobs.queue import get_job_queue

    items = get_job_queue().list_jobs(limit=10)
    if not items:
        return SlashResult(ok=True, message="No jobs queued.")
    lines = [f"- {item['job_id']} [{item['status']}] {item['job_type']}" for item in items]
    return SlashResult(ok=True, message="Jobs:\n" + "\n".join(lines))


async def _research_project(ctx: SlashContext) -> SlashResult:
    from keprix.research_workspace.store import get_research_workspace_store

    title = " ".join(ctx.args).strip() or "Research project"
    project = get_research_workspace_store().create_project(title=title)
    return SlashResult(ok=True, message=f"Created research project {project.get('project_id')}: {title}")


async def _stats_describe(ctx: SlashContext) -> SlashResult:
    if len(ctx.args) < 2:
        return SlashResult(ok=False, message="Usage: /stats describe <dataset_id> <column>")
    from keprix.analytics.statistical_methods import describe
    from keprix.data_plane.catalog import get_dataset_catalog
    import csv
    from pathlib import Path

    dataset_id, column = ctx.args[0], ctx.args[1]
    row = get_dataset_catalog().get(dataset_id)
    if row is None:
        return SlashResult(ok=False, message="Dataset not found")
    values: list[float] = []
    with Path(str(row["path"])).open(newline="", encoding="utf-8") as handle:
        for record in csv.DictReader(handle):
            raw = record.get(column)
            if raw:
                try:
                    values.append(float(raw))
                except ValueError:
                    pass
    summary = describe(values)
    return SlashResult(ok=True, message=f"Describe {column}: {summary}")


async def _jobs_retry(ctx: SlashContext) -> SlashResult:
    job_id = ctx.args[0] if ctx.args else ""
    if not job_id:
        return SlashResult(ok=False, message="Usage: /jobs retry <job_id>")
    from keprix.jobs.queue import get_job_queue

    job = get_job_queue().get(job_id)
    if job is None:
        return SlashResult(ok=False, message=f"Job not found: {job_id}")
    if job["status"] != "dead_letter":
        return SlashResult(ok=False, message=f"Job {job_id} is not in dead_letter state")
    return SlashResult(
        ok=True,
        message=f"Retry {job_id} after confirmation via POST /api/jobs with payload replay.",
        requires_confirmation=True,
        risk_level="medium",
    )


async def _research_export_obsidian(ctx: SlashContext) -> SlashResult:
    project_id = ctx.args[0] if ctx.args else ""
    if not project_id:
        return SlashResult(ok=False, message="Usage: /research export obsidian <project_id>")
    return SlashResult(
        ok=True,
        message=f"Export project {project_id} via POST /api/research/projects/{project_id}/export/obsidian",
    )


async def _stats_codebook(ctx: SlashContext) -> SlashResult:
    dataset_id = ctx.args[0] if ctx.args else ""
    if not dataset_id:
        return SlashResult(ok=False, message="Usage: /stats codebook <dataset_id>")
    from keprix.research_workspace.datasets.dataset import DatasetManager

    manager = DatasetManager()
    detail = manager.get_dataset(dataset_id, version_number=1)
    if detail is None:
        return SlashResult(ok=False, message=f"Dataset not found: {dataset_id}")
    variables = detail.get("codebook", {}).get("variables", [])
    return SlashResult(
        ok=True,
        message=f"Codebook for {dataset_id}: {len(variables)} variables. See GET /api/research/datasets/{dataset_id}",
    )


async def _ml_experiment(ctx: SlashContext) -> SlashResult:
    dataset_id = ctx.args[0] if ctx.args else ""
    if not dataset_id:
        return SlashResult(ok=False, message="Usage: /ml experiment <dataset_id>")
    from keprix.ml_workspace.store import get_ml_workspace_store

    experiment = get_ml_workspace_store().create_experiment(
        name=f"Experiment on {dataset_id}",
        task_type="classification",
        dataset_id=dataset_id,
        parameters={"created_via": "slash"},
    )
    return SlashResult(
        ok=True,
        message=f"Created experiment {experiment.get('experiment_id')} for dataset {dataset_id}",
    )


async def _ml_runs(ctx: SlashContext) -> SlashResult:
    from keprix.ml_workspace.store import get_ml_workspace_store

    runs = get_ml_workspace_store().list_runs()[:10]
    if not runs:
        return SlashResult(ok=True, message="No ML runs yet.")
    lines = [f"- {run['run_id']} ({run['status']}) exp={run['experiment_id']}" for run in runs]
    return SlashResult(ok=True, message="ML runs:\n" + "\n".join(lines))


async def _language(ctx: SlashContext) -> SlashResult:
    from keprix.backend.localization.slash import execute_language_slash

    result = await execute_language_slash(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        args=list(ctx.args),
    )
    return SlashResult(ok=result.ok, message=result.message, payload=result.payload or {})


async def _crew(ctx: SlashContext) -> SlashResult:
    from keprix.slash.commands.crew import handle_crew_slash

    return await handle_crew_slash(ctx)



async def _vical_slots(ctx: SlashContext) -> SlashResult:
    from keprix.tools.mesh_workspace_tools import _handle_vical_slots

    count = 5
    if ctx.args:
        try:
            count = int(str(ctx.args[0]))
        except ValueError:
            count = 5
    raw = _handle_vical_slots({"user_id": ctx.user_id, "count": count})
    return SlashResult(ok=True, message=raw)


async def _vical_bookings(ctx: SlashContext) -> SlashResult:
    from keprix.tools.mesh_workspace_tools import _handle_vical_cancel, _handle_vical_list

    if ctx.args and str(ctx.args[0]).lower() == "cancel" and len(ctx.args) >= 2:
        raw = _handle_vical_cancel({"user_id": ctx.user_id, "booking_id": str(ctx.args[1])})
        return SlashResult(ok=True, message=raw)
    raw = _handle_vical_list({"user_id": ctx.user_id, "limit": 10})
    return SlashResult(ok=True, message=raw)


def register_builtin_commands(registry: SlashRegistry) -> None:
    entries = [
        SlashCommand("help", description="Show available commands", usage="/help", category="general", min_role="viewer", handler=_help),
        SlashCommand("status", description="Show agent and gateway status", usage="/status", category="general", min_role="viewer", handler=_status),
        SlashCommand("whoami", description="Show current identity", usage="/whoami", category="general", min_role="viewer", handler=_whoami),
        SlashCommand("memory.search", aliases=["memory"], description="Search user memory", usage="/memory search <query>", category="memory", min_role="viewer", handler=_memory_search),
        SlashCommand("memory.save", description="Save a memory", usage='/memory save "text"', category="memory", min_role="operator", requires_confirmation=True, risk_level="medium", handler=_memory_save),
        SlashCommand("playbook.scan", aliases=["playbook"], description="Run hardware scan", usage="/playbook scan", category="playbook", min_role="viewer", handler=_playbook_scan),
        SlashCommand("playbook.models", description="List recommended local models", usage="/playbook models", category="playbook", min_role="viewer", handler=_playbook_models),
        SlashCommand("playbook.serve", description="Start a local model backend", usage="/playbook serve <model>", category="playbook", min_role="admin", requires_confirmation=True, risk_level="high", handler=_playbook_serve),
        SlashCommand("tools", description="List enabled tools", usage="/tools", category="tools", min_role="viewer", handler=_tools),
        SlashCommand("tool.run", aliases=["tool"], description="Run a named tool", usage="/tool run <name> <json>", category="tools", min_role="admin", requires_confirmation=True, risk_level="high", handler=_tool_run),
        SlashCommand("research", description="Start deep research", usage='/research "query"', category="research", min_role="operator", requires_confirmation=True, risk_level="medium", handler=_research),
        SlashCommand("settings", description="Show settings summary", usage="/settings", category="settings", min_role="viewer", handler=_settings),
        SlashCommand("settings.set", description="Change a setting", usage="/settings set <key> <value>", category="settings", min_role="admin", requires_confirmation=True, risk_level="high", handler=_settings_set),
        SlashCommand("channels", description="Show connected channels", usage="/channels", category="channels", min_role="viewer", handler=_channels),
        SlashCommand("governance.status", aliases=["governance"], description="Show governance status", usage="/governance status", category="governance", min_role="viewer", handler=_governance_status),
        SlashCommand("data.import", description="Start guided data import", usage="/data import", category="data", min_role="operator", handler=_data_import),
        SlashCommand("data.profile", aliases=["data"], description="Profile a dataset", usage="/data profile <dataset>", category="data", min_role="viewer", handler=_data_profile),
        SlashCommand("data.export", description="Export a dataset", usage="/data export <dataset>", category="data", min_role="operator", handler=_data_export),
        SlashCommand("jobs", description="Show active and failed jobs", usage="/jobs", category="jobs", min_role="viewer", handler=_jobs_list),
        SlashCommand("jobs.retry", description="Retry a failed job", usage="/jobs retry <job>", category="jobs", min_role="admin", requires_confirmation=True, risk_level="high", handler=_jobs_retry),
        SlashCommand("research.project", description="Create research project", usage='/research project "title"', category="research", min_role="operator", handler=_research_project),
        SlashCommand("research.export.obsidian", description="Export research project to Obsidian", usage="/research export obsidian <project>", category="research", min_role="operator", handler=_research_export_obsidian),
        SlashCommand("stats.describe", description="Descriptive statistics", usage="/stats describe <dataset> <column>", category="stats", min_role="viewer", handler=_stats_describe),
        SlashCommand("stats.codebook", description="Generate a codebook", usage="/stats codebook <dataset>", category="stats", min_role="viewer", handler=_stats_codebook),
        SlashCommand("ml.experiment", description="Start an ML experiment", usage="/ml experiment <dataset>", category="ml", min_role="operator", handler=_ml_experiment),
        SlashCommand("ml.runs", description="Show ML experiment runs", usage="/ml runs", category="ml", min_role="viewer", handler=_ml_runs),
        SlashCommand("opportunity", description="Run Opportunity Engine playbooks", usage='/opportunity find demand for "niche"', category="playbook", min_role="operator", handler=_opportunity),
        SlashCommand("slots", description="Show viCal available slots", usage="/slots [count]", category="vical", min_role="viewer", handler=_vical_slots),
        SlashCommand("bookings", description="List or cancel viCal bookings", usage="/bookings [cancel <id>]", category="vical", min_role="operator", handler=_vical_bookings),
        SlashCommand("crew", description="Run a registered agent team", usage='/crew <team_id> "objective"', category="playbook", min_role="operator", handler=_crew),
        SlashCommand("language", description="Show or set language preferences", usage="/language set tw-GH", category="settings", min_role="viewer", handler=_language),
        SlashCommand("safety", description="Show safety rules", usage="/safety", category="safety", min_role="viewer", handler=_safety),
        SlashCommand("approve", description="Approve a pending command", usage="/approve <token>", category="safety", min_role="viewer", handler=_approve),
        SlashCommand("cancel", description="Cancel a pending command", usage="/cancel <token>", category="safety", min_role="viewer", handler=_cancel),
        SlashCommand("diagnostics", description="Show diagnostics", usage="/diagnostics", category="diagnostics", min_role="admin", handler=_diagnostics),
        SlashCommand(
            "leads",
            aliases=["leads.find", "leads.approve", "leads.digest"],
            description="CRM funnel: find / approve Soft Wall / digest",
            usage="/leads find <query> [in place] | /leads approve [id] | /leads digest",
            category="crm",
            min_role="operator",
            handler=_crm_leads,
        ),
        SlashCommand(
            "crm",
            aliases=["crm.ask"],
            description="Ask CRM questions from channel",
            usage='/crm ask "who is engaged?"',
            category="crm",
            min_role="viewer",
            handler=_crm_ask,
        ),
        SlashCommand(
            "vault",
            aliases=["vault.list", "vault.search", "vault.status"],
            description="Document Vault over channels (Telegram and matrix)",
            usage="/vault status | list | search <q> | mkdir <name> | create <name> | export <id> | import | bind <ws>",
            category="document-vault",
            min_role="viewer",
            handler=_vault_channel,
        ),
    ]
    for entry in entries:
        registry.register(entry)


async def _crm_leads(ctx: SlashContext) -> SlashResult:
    from keprix.crm.telegram_funnel import handle_leads_command

    return await handle_leads_command(ctx)


async def _crm_ask(ctx: SlashContext) -> SlashResult:
    from keprix.crm.telegram_funnel import handle_crm_command

    return await handle_crm_command(ctx)


async def _vault_channel(ctx: SlashContext) -> SlashResult:
    from keprix.document_vault.channel.commands import handle_vault_channel_command

    return await handle_vault_channel_command(ctx)
