"""Filesystem workspace management for opportunity mode."""

from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.opportunity.models import (
    ARTIFACT_FILENAMES,
    ASSET_FOLDER_FILENAMES,
    OpportunityRequest,
    OpportunityWorkspace,
)
from keprix.security.validation import ValidationError, default_validator
from keprix.workspace.core.atomic_io import atomic_write_json
from keprix.workspace.core.constants import WORKSPACE_ROOT

OPPORTUNITY_ID_RE = re.compile(r"^opp-[a-z0-9]{8}$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def opportunities_root() -> Path:
    root = Path(WORKSPACE_ROOT) / "opportunities"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sanitize_slug(value: str) -> str:
    cleaned = default_validator.validate_string(value, "slug", max_length=80).lower()
    slug = _SLUG_RE.sub("-", cleaned).strip("-")
    if not slug:
        slug = "opportunity"
    return slug[:60]


def generate_opportunity_id() -> str:
    return "opp-" + secrets.token_hex(4)


def _artifact_template(filename: str, *, title: str, niche: str, goal: str) -> str:
    label = filename.replace(".md", "").replace("-", " ").title()
    return (
        f"# {label}\n\n"
        f"Opportunity: {title}\n"
        f"Niche: {niche or 'TBD'}\n"
        f"Goal: {goal or 'TBD'}\n\n"
        f"Status: pending phase execution.\n"
    )


def _default_opportunity_json(
    *,
    workspace_id: str,
    opportunity_id: str,
    slug: str,
    request: OpportunityRequest,
) -> dict[str, Any]:
    now = _utcnow_iso()
    return {
        "workspace_id": workspace_id,
        "opportunity_id": opportunity_id,
        "slug": slug,
        "title": request.title,
        "niche": request.niche,
        "market": request.market,
        "goal": request.goal,
        "geography": request.geography,
        "buyer_type": request.buyer_type,
        "budget_range": request.budget_range,
        "exclusions": request.exclusions,
        "research_depth": request.research_depth,
        "status": "draft",
        "current_phase": None,
        "completed_phases": [],
        "offer_outline": {},
        "citations": [],
        "scores": {},
        "pending_approvals": [],
        "created_at": now,
        "updated_at": now,
        "source": request.source,
    }


def _resolve_opportunity_dir(opportunity_id: str) -> Path:
    if not OPPORTUNITY_ID_RE.fullmatch(opportunity_id):
        raise ValidationError(f"Invalid opportunity_id: {opportunity_id!r}")
    base = opportunities_root().resolve()
    candidate = (base / opportunity_id).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValidationError("opportunity path escapes opportunities root") from exc
    return candidate


def _validate_artifact_filename(filename: str) -> str:
    cleaned = default_validator.validate_string(filename, "filename", max_length=120)
    if cleaned not in ARTIFACT_FILENAMES:
        raise ValidationError(f"Unknown artifact filename: {cleaned!r}")
    base = opportunities_root().resolve()
    default_validator.validate_path(cleaned, "filename", str(base))
    return cleaned


def create_opportunity_workspace(request: OpportunityRequest) -> OpportunityWorkspace:
    opportunity_id = generate_opportunity_id()
    base = opportunities_root()
    while (base / opportunity_id).exists():
        opportunity_id = generate_opportunity_id()

    slug = _sanitize_slug(request.title)
    opp_dir = _resolve_opportunity_dir(opportunity_id)
    opp_dir.mkdir(parents=True, exist_ok=False)

    niche = request.niche or request.market or ""
    goal = request.goal or request.title
    for filename in ARTIFACT_FILENAMES:
        if filename == "opportunity.json":
            continue
        if filename == "13-approval-log.md":
            content = "# Approval Log\n\n| Timestamp | Action | Status | Actor |\n|---|---|---|---|\n"
        else:
            content = _artifact_template(filename, title=request.title, niche=niche, goal=goal)
        (opp_dir / filename).write_text(content, encoding="utf-8")

    meta = _default_opportunity_json(
        workspace_id=request.workspace_id,
        opportunity_id=opportunity_id,
        slug=slug,
        request=request,
    )
    atomic_write_json(opp_dir / "opportunity.json", meta)

    now = datetime.now(timezone.utc)
    return OpportunityWorkspace(
        workspace_id=request.workspace_id,
        opportunity_id=opportunity_id,
        slug=slug,
        title=request.title,
        niche=request.niche,
        market=request.market,
        goal=request.goal,
        status="draft",
        path=str(opp_dir),
        source=request.source,
        created_at=now,
        updated_at=now,
    )


def load_opportunity_workspace(opportunity_id: str) -> OpportunityWorkspace:
    opp_dir = _resolve_opportunity_dir(opportunity_id)
    meta_path = opp_dir / "opportunity.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Opportunity workspace not found: {opportunity_id}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    created = datetime.fromisoformat(meta["created_at"])
    updated = datetime.fromisoformat(meta["updated_at"])
    return OpportunityWorkspace(
        workspace_id=meta["workspace_id"],
        opportunity_id=meta["opportunity_id"],
        slug=meta.get("slug", opportunity_id),
        title=meta.get("title", ""),
        niche=meta.get("niche"),
        market=meta.get("market"),
        goal=meta.get("goal"),
        status=meta.get("status", "draft"),
        current_phase=meta.get("current_phase"),
        completed_phases=meta.get("completed_phases", []),
        path=str(opp_dir),
        source=meta.get("source", "api"),
        created_at=created,
        updated_at=updated,
    )


def _validate_asset_filename(filename: str) -> str:
    cleaned = default_validator.validate_string(filename, "filename", max_length=120)
    if cleaned not in ASSET_FOLDER_FILENAMES:
        raise ValidationError(f"Unknown asset filename: {cleaned!r}")
    base = opportunities_root().resolve()
    default_validator.validate_path(f"assets/{cleaned}", "filename", str(base))
    return cleaned


def write_opportunity_asset(opportunity_id: str, filename: str, content: str) -> None:
    safe_name = _validate_asset_filename(filename)
    opp_dir = _resolve_opportunity_dir(opportunity_id)
    assets_dir = opp_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    path = (assets_dir / safe_name).resolve()
    try:
        path.relative_to(assets_dir.resolve())
    except ValueError as exc:
        raise ValidationError("asset path escapes assets directory") from exc
    path.write_text(content, encoding="utf-8")


def read_opportunity_asset(opportunity_id: str, filename: str) -> str:
    safe_name = _validate_asset_filename(filename)
    opp_dir = _resolve_opportunity_dir(opportunity_id)
    path = opp_dir / "assets" / safe_name
    if not path.exists():
        raise FileNotFoundError(f"Asset not found: assets/{safe_name}")
    return path.read_text(encoding="utf-8")


def write_artifact(
    opportunity_id: str,
    filename: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    safe_name = _validate_artifact_filename(filename)
    opp_dir = _resolve_opportunity_dir(opportunity_id)
    path = opp_dir / safe_name
    default_validator.validate_path(safe_name, "filename", str(opp_dir.resolve()))
    path.write_text(content, encoding="utf-8")
    if metadata:
        sidecar = opp_dir / f".{safe_name}.meta.json"
        atomic_write_json(sidecar, metadata)


def read_artifact(opportunity_id: str, filename: str) -> str:
    safe_name = _validate_artifact_filename(filename)
    opp_dir = _resolve_opportunity_dir(opportunity_id)
    path = opp_dir / safe_name
    default_validator.validate_path(safe_name, "filename", str(opp_dir.resolve()))
    if not path.exists():
        raise FileNotFoundError(f"Artifact not found: {safe_name}")
    return path.read_text(encoding="utf-8")


def append_approval_log(opportunity_id: str, event: dict[str, Any]) -> None:
    opp_dir = _resolve_opportunity_dir(opportunity_id)
    log_path = opp_dir / "13-approval-log.md"
    timestamp = event.get("timestamp") or _utcnow_iso()
    action = str(event.get("action", "")).replace("|", "/")
    status = str(event.get("status", "")).replace("|", "/")
    actor = str(event.get("actor", "")).replace("|", "/")
    line = f"| {timestamp} | {action} | {status} | {actor} |\n"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        if event.get("risk_level") or event.get("preview"):
            handle.write(
                f"\n**Detail** ({timestamp})\n"
                f"- Risk level: {event.get('risk_level', 'n/a')}\n"
                f"- Preview: {event.get('preview', '')}\n"
                f"- Integration: {event.get('integration', 'n/a')}\n"
                f"- Requested by: {event.get('requested_by', actor)}\n"
                f"- Approved by: {event.get('approved_by', '')}\n"
                f"- Result: {event.get('result', status)}\n\n"
            )


def update_opportunity_json(opportunity_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    opp_dir = _resolve_opportunity_dir(opportunity_id)
    meta_path = opp_dir / "opportunity.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Opportunity workspace not found: {opportunity_id}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update(patch)
    meta["updated_at"] = _utcnow_iso()
    atomic_write_json(meta_path, meta)
    return meta


def read_opportunity_json(opportunity_id: str) -> dict[str, Any]:
    opp_dir = _resolve_opportunity_dir(opportunity_id)
    meta_path = opp_dir / "opportunity.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Opportunity workspace not found: {opportunity_id}")
    return json.loads(meta_path.read_text(encoding="utf-8"))
