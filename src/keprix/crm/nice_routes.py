"""HTTP routes for Nice P5 CRM features (/api/crm/* extensions)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.crm.roles import require_cap
from keprix.crm.store import get_crm_store

router = APIRouter(prefix="/api/crm", tags=["crm-nice"])


def _uid(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


def _workspace(workspace_id: str | None, x_workspace_id: str | None, user: dict[str, Any]) -> str:
    return (workspace_id or x_workspace_id or _uid(user) or "default").strip() or "default"


def _store():
    return get_crm_store()


# ---- 453 assignment / SLA ----
class TeamCreate(BaseModel):
    name: str
    member_user_ids: list[str] = Field(default_factory=list)


class AssignBody(BaseModel):
    entity_type: str
    entity_id: str
    owner_user_id: str | None = None
    team_id: str | None = None
    mode: str = "manual"
    sla_hours: int | None = 24
    force: bool = False
    approval_id: str | None = None


class LockBody(BaseModel):
    entity_type: str
    entity_id: str
    ttl_seconds: int = 120


class CommentBody(BaseModel):
    entity_type: str
    entity_id: str
    body: str
    mentions: list[str] = Field(default_factory=list)


@router.get("/sla/inbox")
def sla_inbox_route(
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.assignment import sla_inbox

    return sla_inbox(_store(), _workspace(workspace_id, x_workspace_id, user))


@router.get("/teams")
def list_teams_route(
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.assignment import list_teams

    items = list_teams(_store(), _workspace(workspace_id, x_workspace_id, user))
    return {"items": items, "count": len(items)}


@router.post("/teams")
def create_team_route(
    body: TeamCreate,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.assignment import ensure_team

    team = ensure_team(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        name=body.name,
        member_user_ids=body.member_user_ids,
    )
    return {"ok": True, "team": team}


@router.post("/assign")
def assign_route(
    body: AssignBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.assignment import assign_owner

    return assign_owner(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        actor_id=_uid(user),
        **body.model_dump(),
    )


@router.post("/locks")
def lock_route(
    body: LockBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.assignment import acquire_lock

    return acquire_lock(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        owner_user_id=_uid(user),
        ttl_seconds=body.ttl_seconds,
    )


@router.delete("/locks")
def unlock_route(
    entity_type: str,
    entity_id: str,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.assignment import release_lock

    return release_lock(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        entity_type=entity_type,
        entity_id=entity_id,
        owner_user_id=_uid(user),
    )


@router.post("/comments")
def comment_route(
    body: CommentBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.assignment import add_comment

    row = add_comment(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        body=body.body,
        mentions=body.mentions,
        actor_type="user",
        actor_id=_uid(user),
    )
    return {"ok": True, "comment": row}


@router.get("/comments")
def list_comments_route(
    entity_type: str,
    entity_id: str,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.assignment import list_comments

    items = list_comments(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return {"items": items, "count": len(items)}


# ---- 454 integrations ----
class ImportBody(BaseModel):
    provider: str = "csv"
    payload: Any
    force: bool = False
    approval_id: str | None = None


@router.get("/integrations")
def integrations_status(
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.integrations import FIELD_MAPPING_DOCS, list_adapters

    ws = _workspace(workspace_id, x_workspace_id, user)
    return {
        "adapters": list_adapters(ws),
        "field_mappings": FIELD_MAPPING_DOCS,
        "configure_path": "/crm/settings#connections",
    }


@router.get("/connections")
def connections_get(
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.connections import connections_status, list_catalog

    ws = _workspace(workspace_id, x_workspace_id, user)
    return {
        "catalog": list_catalog(),
        "status": connections_status(_store(), ws),
    }


class CredentialPut(BaseModel):
    slot_id: str
    value: str
    label: str | None = None


class FlagPut(BaseModel):
    flag_id: str
    enabled: bool


@router.put("/connections/credentials")
def connections_put_credential(
    body: CredentialPut,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.connections import put_credential

    try:
        slot = put_credential(
            _store(),
            _workspace(workspace_id, x_workspace_id, user),
            body.slot_id,
            body.value,
            actor_type="user",
            actor_id=_uid(user),
            label=body.label,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error_code": str(exc)}) from exc
    return {"ok": True, "slot": slot}


@router.delete("/connections/credentials/{slot_id}")
def connections_delete_credential(
    slot_id: str,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.connections import delete_credential

    return delete_credential(_store(), _workspace(workspace_id, x_workspace_id, user), slot_id)


@router.put("/connections/flags")
def connections_put_flag(
    body: FlagPut,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.connections import set_flag

    try:
        return set_flag(
            _store(),
            _workspace(workspace_id, x_workspace_id, user),
            body.flag_id,
            body.enabled,
            actor_id=_uid(user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error_code": str(exc)}) from exc



@router.post("/integrations/preview")
def integrations_preview(
    body: ImportBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.integrations import preview_import

    return preview_import(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        provider=body.provider,
        payload=body.payload,
    )


@router.post("/integrations/import")
def integrations_import(
    body: ImportBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.integrations import apply_import

    return apply_import(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        provider=body.provider,
        payload=body.payload,
        actor_id=_uid(user),
        force=body.force,
        approval_id=body.approval_id,
    )


@router.get("/integrations/export")
def integrations_export(
    provider: str = "csv",
    list_id: str | None = None,
    stage: str | None = None,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.integrations import export_list_or_stage

    return export_list_or_stage(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        provider=provider,
        list_id=list_id,
        stage=stage,
    )


# ---- 455 experiments ----
class ExperimentCreate(BaseModel):
    name: str
    variants: list[dict[str, Any]]
    traffic_split: dict[str, float] | None = None
    sequence_id: str | None = None
    min_sample: int = 50


@router.get("/experiments")
def list_experiments_route(
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.experiments import list_experiments

    items = list_experiments(_store(), _workspace(workspace_id, x_workspace_id, user))
    return {"items": items, "count": len(items)}


@router.post("/experiments")
def create_experiment_route(
    body: ExperimentCreate,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.experiments import create_experiment

    row = create_experiment(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        actor_id=_uid(user),
        **body.model_dump(),
    )
    return {"ok": True, "experiment": row}


@router.get("/experiments/{experiment_id}/results")
def experiment_results_route(
    experiment_id: str,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.experiments import results_table

    return results_table(_store(), _workspace(workspace_id, x_workspace_id, user), experiment_id)


@router.post("/experiments/{experiment_id}/promote")
def experiment_promote_route(
    experiment_id: str,
    winner_variant: str = Body(..., embed=True),
    force: bool = False,
    approval_id: str | None = None,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.experiments import promote_winner

    return promote_winner(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        experiment_id,
        winner_variant=winner_variant,
        actor_id=_uid(user),
        force=force,
        approval_id=approval_id,
    )


# ---- 456 licensed enrich ----
class EnrichPropose(BaseModel):
    provider: str = "fake_licensed"
    batch: list[dict[str, Any]]


@router.get("/enrich/providers")
def enrich_providers_route(
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.licensed_enrich import list_providers

    ws = _workspace(workspace_id, x_workspace_id, user)
    return {
        "providers": list_providers(ws),
        "configure_path": "/crm/settings#connections",
    }


@router.post("/enrich/providers/propose")
def enrich_propose_route(
    body: EnrichPropose,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.licensed_enrich import propose_enrich

    return propose_enrich(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        provider=body.provider,
        batch=body.batch,
        actor_id=_uid(user),
    )


@router.post("/enrich/providers/{run_id}/apply")
def enrich_apply_route(
    run_id: str,
    force: bool = False,
    approval_id: str | None = None,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.licensed_enrich import apply_enrich

    return apply_enrich(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        run_id,
        actor_id=_uid(user),
        force=force,
        approval_id=approval_id,
    )


@router.post("/enrich/providers/{run_id}/reject")
def enrich_reject_route(
    run_id: str,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.licensed_enrich import reject_enrich

    return reject_enrich(_store(), _workspace(workspace_id, x_workspace_id, user), run_id)


# ---- 457 data quality ----
@router.get("/data-quality")
def data_quality_route(
    pack: str | None = None,
    stage: str | None = None,
    owner: str | None = None,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.data_quality import quality_summary

    return quality_summary(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        pack=pack,
        stage=stage,
        owner=owner,
    )


@router.post("/data-quality/reverify")
def data_quality_reverify(
    filters: dict[str, Any] | None = Body(default=None),
    force: bool = False,
    approval_id: str | None = None,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.data_quality import create_reverify_job

    return create_reverify_job(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        filters=filters or {},
        actor_id=_uid(user),
        force=force,
        approval_id=approval_id,
    )


# ---- 458 multilingual ----
class LocaleBody(BaseModel):
    sequence_id: str
    step_order: int = 1
    locale: str
    subject: str | None = None
    body: str | None = None
    force: bool = False
    approval_id: str | None = None


@router.get("/locales")
def list_locales_route(
    sequence_id: str | None = None,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.multilingual import list_locale_variants

    items = list_locale_variants(
        _store(), _workspace(workspace_id, x_workspace_id, user), sequence_id=sequence_id
    )
    return {"items": items, "count": len(items)}


@router.post("/locales")
def upsert_locale_route(
    body: LocaleBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.multilingual import upsert_locale_variant

    return upsert_locale_variant(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        actor_id=_uid(user),
        **body.model_dump(),
    )


@router.post("/locales/resolve")
def resolve_locale_route(
    sequence_id: str = Body(...),
    step_order: int = Body(1),
    preferred_locale: str | None = Body(None),
    default_step: dict[str, Any] | None = Body(None),
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.multilingual import resolve_step_copy

    return resolve_step_copy(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        sequence_id=sequence_id,
        step_order=step_order,
        preferred_locale=preferred_locale,
        default_step=default_step,
    )


# ---- 459 messaging ----
@router.get("/messaging/status")
def messaging_status_route(
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.data_quality import get_nice_settings
    from keprix.crm.messaging_channels import list_templates, provider_status

    ws = _workspace(workspace_id, x_workspace_id, user)
    return {
        "provider": provider_status(ws),
        "settings": get_nice_settings(_store(), ws),
        "templates": list_templates(_store(), ws),
        "configure_path": "/crm/settings#connections",
    }


class MessageSend(BaseModel):
    channel: str
    subject_type: str
    subject_id: str
    address: str
    template_id: str | None = None
    body: str | None = None
    first_touch: bool = True
    force: bool = False
    approval_id: str | None = None


class MessageEnable(BaseModel):
    enabled: bool
    force: bool = False
    approval_id: str | None = None


class MessageTemplate(BaseModel):
    channel: str
    name: str
    body: str
    provider_template_id: str | None = None
    force: bool = False
    approval_id: str | None = None


@router.post("/messaging/enable")
def messaging_enable_route(
    body: MessageEnable,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "approve")
    from keprix.crm.messaging_channels import enable_workspace_channels

    return enable_workspace_channels(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        enabled=body.enabled,
        actor_id=_uid(user),
        force=body.force,
        approval_id=body.approval_id,
    )


@router.get("/messaging/templates")
def messaging_templates_route(
    channel: str | None = None,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.messaging_channels import list_templates

    items = list_templates(_store(), _workspace(workspace_id, x_workspace_id, user), channel=channel)
    return {"items": items, "count": len(items)}


@router.post("/messaging/templates")
def messaging_template_create_route(
    body: MessageTemplate,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.messaging_channels import register_template

    return register_template(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        actor_id=_uid(user),
        **body.model_dump(),
    )


@router.post("/messaging/send")
def messaging_send_route(
    body: MessageSend,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.messaging_channels import send_channel_message

    return send_channel_message(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        actor_id=_uid(user),
        **body.model_dump(),
    )


# ---- 460 tracking ----
@router.get("/tracking/settings")
def tracking_settings_get(
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.data_quality import get_nice_settings

    return get_nice_settings(_store(), _workspace(workspace_id, x_workspace_id, user))


@router.put("/tracking/settings")
def tracking_settings_put(
    enabled: bool = Body(..., embed=True),
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.tracking import set_workspace_tracking

    return {"ok": True, "settings": set_workspace_tracking(_store(), _workspace(workspace_id, x_workspace_id, user), enabled)}


@router.post("/tracking/wrap")
def tracking_wrap_route(
    body_text: str = Body(..., alias="body"),
    campaign_id: str | None = Body(None),
    contact_key: str | None = Body(None),
    campaign_override: bool | None = Body(None),
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.tracking import wrap_links

    return wrap_links(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        html_or_text=body_text,
        campaign_id=campaign_id,
        contact_key=contact_key,
        campaign_override=campaign_override,
    )


@router.get("/tracking/click")
def tracking_click(t: str, workspace_id: str = Query("default")) -> Response:
    from keprix.crm.tracking import record_event, resolve_click

    meta = resolve_click(t) or {}
    ws = str(meta.get("workspace_id") or workspace_id)
    record_event(_store(), ws, event_type="click", token=t)
    target = meta.get("raw_url") or "/"
    return Response(status_code=302, headers={"Location": str(target)})


@router.get("/tracking/open.gif")
def tracking_open(t: str, workspace_id: str = Query("default")) -> Response:
    from keprix.crm.tracking import record_event, resolve_click

    meta = resolve_click(t) or {}
    ws = str(meta.get("workspace_id") or workspace_id)
    record_event(_store(), ws, event_type="open", token=t)
    # 1x1 gif
    pixel = (
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00"
        b",\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    )
    return Response(content=pixel, media_type="image/gif")


# ---- 461 social health ----
@router.get("/social/health")
def social_health_route(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.discovery.adapters.social import LinkedInApiAdapter, MetaGraphAdapter, TikTokApiAdapter, scrape_refusal_payload

    adapters = [LinkedInApiAdapter(), MetaGraphAdapter(), TikTokApiAdapter()]
    return {
        "adapters": [a.health().to_dict() for a in adapters],
        "scrape": scrape_refusal_payload(),
    }


# ---- 462 voice ----
class CallNoteBody(BaseModel):
    entity_type: str
    entity_id: str
    duration_seconds: int | None = None
    outcome: str | None = None
    next_step: str | None = None
    body: str | None = None


class VoiceBody(BaseModel):
    entity_type: str | None = None
    entity_id: str | None = None
    media_path: str | None = None
    transcript: str | None = None
    stt_configured: bool = False
    consent_recorded: bool = False


@router.post("/voice/call-note")
def call_note_route(
    body: CallNoteBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.voice_notes import create_call_note

    return create_call_note(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        actor_id=_uid(user),
        **body.model_dump(),
    )


@router.post("/voice/note")
def voice_note_route(
    body: VoiceBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.voice_notes import attach_voice_note

    return attach_voice_note(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        actor_id=_uid(user),
        **body.model_dump(),
    )


@router.post("/voice/retention/run")
def voice_retention_route(
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.voice_notes import run_retention_job

    return run_retention_job(_store(), _workspace(workspace_id, x_workspace_id, user))


# ---- 463 scoring ----
@router.post("/icp/score")
def score_icp_route(
    entity_type: str = Body(...),
    entity_id: str = Body(...),
    icp_id: str | None = Body(None),
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.icp_scoring import score_entity

    return score_entity(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        entity_type=entity_type,
        entity_id=entity_id,
        icp_id=icp_id,
    )


@router.post("/icp/brief")
def brief_route(
    entity_type: str = Body(...),
    entity_id: str = Body(...),
    icp_id: str | None = Body(None),
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.icp_scoring import generate_account_brief

    return generate_account_brief(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        entity_type=entity_type,
        entity_id=entity_id,
        icp_id=icp_id,
    )


# ---- 464 property portals ----
@router.get("/property-portals/status")
def portals_status(
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.property_portal_gate import portal_gate_status

    return portal_gate_status(_store(), _workspace(workspace_id, x_workspace_id, user))


@router.post("/property-portals/acknowledge")
def portals_ack(
    notes: str | None = Body(None),
    force: bool = False,
    approval_id: str | None = None,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.property_portal_gate import acknowledge_checklist

    return acknowledge_checklist(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        acknowledged_by=_uid(user),
        notes=notes,
        actor_id=_uid(user),
        force=force,
        approval_id=approval_id,
    )


@router.post("/property-portals/kill-switch")
def portals_kill(
    engaged: bool = Body(..., embed=True),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.property_portal_gate import set_kill_switch

    return set_kill_switch(engaged)


# ---- 465 attribution ----
class AttributionBody(BaseModel):
    mode: str
    notes: str | None = None
    stripe_customer_id: str | None = None


@router.post("/deals/{deal_id}/attribution")
def deal_attribution_route(
    deal_id: str,
    body: AttributionBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    from keprix.crm.attribution import set_deal_attribution

    return set_deal_attribution(
        _store(),
        _workspace(workspace_id, x_workspace_id, user),
        deal_id,
        **body.model_dump(),
    )


@router.get("/attribution/report")
def attribution_report_route(
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    from keprix.crm.attribution import attribution_report

    return attribution_report(_store(), _workspace(workspace_id, x_workspace_id, user))


@router.get("/nice/matrix")
def nice_matrix_route(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    require_cap(user, "view")
    return {
        "docs": "docs/architecture/agentic-crm-nice-signoff.md",
        "prompts": {
            "451": "satisfied_by_508",
            "452": "shipped",
            "453": "shipped",
            "454": "shipped_degraded_without_keys",
            "455": "shipped",
            "456": "shipped_degraded_without_keys",
            "457": "shipped",
            "458": "shipped",
            "459": "shipped_flag_off_default",
            "460": "shipped_opt_in",
            "461": "shipped_degraded_without_keys",
            "462": "shipped",
            "463": "shipped",
            "464": "shipped_flag_off_default",
            "465": "shipped",
        },
    }
