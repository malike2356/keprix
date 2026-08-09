"""Audience ingress helpers for web and gateway channels (Prompt 630)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from keprix.customer_concierge.audience.context import AudiencePrincipalContext, set_audience_context
from keprix.customer_concierge.audience.embed import is_origin_allowed, verify_widget_embed_config
from keprix.customer_concierge.audience.models import is_audience_session_usable
from keprix.customer_concierge.audience.store import get_audience_store
from keprix.customer_concierge.store import get_concierge_store
from keprix.customer_concierge.widget import gate_new_widget_session


SUPPORTED_CHANNELS = frozenset({"web", "telegram", "whatsapp", "email", "sms", "voice"})


def open_audience_session(
    *,
    workspace_id: str,
    persona_id: str,
    channel: str = "web",
    external_key: str | None = None,
    origin: str | None = None,
    locale: str | None = None,
    display_name: str | None = None,
    email: str | None = None,
    embed_token: str | None = None,
    embed_nonce: str | None = None,
    consent_state: str = "unknown",
) -> dict[str, Any]:
    channel = (channel or "web").strip().lower()
    if channel not in SUPPORTED_CHANNELS:
        return {"ok": False, "error_code": "unsupported_channel"}

    profile_store = get_concierge_store()
    profile = profile_store.get(workspace_id, persona_id)
    gate = gate_new_widget_session(profile)
    if not gate["ok"]:
        return gate

    assert profile is not None
    web_cfg = (profile.channel_config or {}).get("web") or {}
    allowlist = list(web_cfg.get("originAllowlist") or [])
    if channel == "web" and not is_origin_allowed(origin, allowlist if allowlist else None):
        return {"ok": False, "error_code": "origin_forbidden"}

    aud = get_audience_store()
    if embed_token:
        verified = verify_widget_embed_config(embed_token, expected_persona_id=persona_id)
        if not verified or str(verified.get("workspaceId")) != workspace_id:
            return {"ok": False, "error_code": "embed_token_invalid"}
        nonce = str(verified.get("nonce") or embed_nonce or "")
        if not nonce or not aud.consume_embed_nonce(
            nonce=nonce, workspace_id=workspace_id, persona_id=persona_id
        ):
            return {"ok": False, "error_code": "embed_nonce_replay"}

    key = (external_key or "").strip() or f"{channel}:{uuid4()}"
    identity = aud.upsert_identity(
        workspace_id=workspace_id,
        channel=channel,
        external_key=key,
        display_name=display_name,
        email=email,
    )
    session = aud.create_session(
        workspace_id=workspace_id,
        persona_id=persona_id,
        concierge_profile_id=profile.id,
        identity_id=identity.id,
        channel=channel,
        session_mode="public",
        origin=origin,
        locale=locale,
        consent_state=consent_state,
    )
    set_audience_context(
        AudiencePrincipalContext(
            workspace_id=workspace_id,
            persona_id=persona_id,
            session_id=session.id,
            identity_id=identity.id,
            channel=channel,
        )
    )
    return {
        "ok": True,
        "session": session.to_dict(),
        "identity": identity.to_dict(),
        "greeting": profile.greeting_message,
        "personaName": profile.persona_name,
        "businessName": profile.business_name,
        "workspaceMember": False,
        "principal": "audience_session",
    }


def resume_audience_session(
    *,
    workspace_id: str,
    persona_id: str,
    session_id: str | None = None,
    widget_token: str | None = None,
) -> dict[str, Any]:
    aud = get_audience_store()
    session = None
    if widget_token:
        session = aud.get_session_by_token(widget_token)
    elif session_id:
        session = aud.get_session(workspace_id, session_id)
    if not session or session.workspace_id != workspace_id or session.persona_id != persona_id:
        return {"ok": False, "error_code": "session_not_found"}
    if not is_audience_session_usable(session):
        return {"ok": False, "error_code": "session_unusable"}
    aud.touch_session(workspace_id, session.id)
    set_audience_context(
        AudiencePrincipalContext(
            workspace_id=workspace_id,
            persona_id=persona_id,
            session_id=session.id,
            identity_id=session.identity_id,
            channel=session.channel,
            session_mode=session.session_mode,
        )
    )
    return {"ok": True, "session": session.to_dict(), "workspaceMember": False}


def check_message_rate(workspace_id: str, session_id: str) -> dict[str, Any]:
    aud = get_audience_store()
    return aud.consume_rate_bucket(
        f"msg:{workspace_id}:{session_id}",
        limit=60,
        window_ms=60_000,
    )
