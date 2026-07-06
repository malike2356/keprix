"""Slash command: /crew (Prompt 195)."""

from __future__ import annotations

from urllib.parse import quote

from keprix.slash.schemas import SlashContext, SlashResult
from keprix.teams.registry import team_registry
from keprix.teams.routes import RunTeamBody, run_team


async def handle_crew_slash(ctx: SlashContext) -> SlashResult:
    if len(ctx.args) < 2:
        return SlashResult(
            ok=False,
            message='Usage: /crew <team_id> <objective>\nExample: /crew sample-crew "Ship the smoke path"',
        )

    team_id = ctx.args[0].strip()
    objective = " ".join(ctx.args[1:]).strip()
    if not team_id or not objective:
        return SlashResult(ok=False, message="Team id and objective are required.")

    if team_registry.get(team_id) is None:
        return SlashResult(
            ok=False,
            message=f"Team `{team_id}` is not registered. Import YAML at /admin/teams first.",
        )

    try:
        result = await run_team(team_id, RunTeamBody(objective=objective))
    except Exception as exc:
        return SlashResult(ok=False, message=f"Crew run failed: {exc}")

    workspace_url = result.get("workspace_url") or f"/admin/teams?team={quote(team_id)}&run={result['run_id']}"
    return SlashResult(
        ok=True,
        message=(
            f"Crew `{team_id}` finished with status `{result['status']}`.\n"
            f"Open: {workspace_url}"
        ),
        data={"run_id": result["run_id"], "workspace_url": workspace_url},
    )
