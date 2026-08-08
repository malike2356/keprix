"""Xeclone sidecar tool handlers (deterministic stubs; no live media providers)."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from approvals.service import submit_preview
from assets.registry import get_asset
from channels.outbox import publish as outbox_publish
from consent.ledger import assert_owner_identity_input, check_consent
from kill_switch.state import is_blocked
from models.router import reject_if_incompatible, route_for
from nodes.catalog import all_nodes, distribution_node_keys
from persona.binding import owner_subject_id, persona_version
from rag.allowlist import search as rag_search
from scout.events import emit_scout_event

_SOURCE = "keprix-xeclone"
# Track whether a generation call attempted distribution (tests assert this stays false)
_LAST_GENERATION_CALLED_DISTRIBUTION = False


def reset_handler_flags() -> None:
    global _LAST_GENERATION_CALLED_DISTRIBUTION
    _LAST_GENERATION_CALLED_DISTRIBUTION = False


def last_generation_called_distribution() -> bool:
    return bool(_LAST_GENERATION_CALLED_DISTRIBUTION)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _labels(
    *,
    stated_facts: dict[str, Any] | None = None,
    private_correspondence: dict[str, Any] | None = None,
    inferred_preferences: dict[str, Any] | None = None,
    generated_style: dict[str, Any] | None = None,
    include_private_in_public: bool = False,
) -> dict[str, Any]:
    private = private_correspondence or {}
    if not include_private_in_public:
        private = {}
    return {
        "stated_facts": stated_facts or {},
        "private_correspondence": private,
        "inferred_preferences": inferred_preferences or {},
        "generated_style": generated_style or {},
    }


def _media_meta(
    *,
    domain: str,
    text: str,
    consent_ids: list[str],
    prompt_template: str,
    fallback_text_only: bool = False,
) -> dict[str, Any]:
    route = route_for(domain)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "job_id": f"mjob_{uuid.uuid4().hex[:10]}",
        "model": route["provider"],
        "version": "stub-0.1.0",
        "source_consent_ids": consent_ids,
        "content_hash": digest,
        "prompt_template": prompt_template,
        "disclosure": True,
        "watermark": True,
        "watermark_removal_blocked": True,
        "storage_expiry": _iso_now(),
        "fallback_text_only": fallback_text_only,
        "provider_training": False,
    }


def _require_consent(args: dict[str, Any], purposes: list[str]) -> dict[str, Any] | None:
    asset_id = str(args.get("asset_id") or "")
    if not asset_id:
        # Text-only drafts without media asset are allowed
        return None
    subject_id = str(args.get("subject_id") or owner_subject_id())
    identity = assert_owner_identity_input(asset_id=asset_id, subject_id=subject_id)
    if not identity.get("ok"):
        return {"status": "error", "error": identity["error"], **identity}
    for purpose in purposes:
        result = check_consent(asset_id, purpose)
        if not result.get("allowed"):
            return {
                "status": "error",
                "error": "consent_denied",
                "purpose": purpose,
                "reason": result.get("reason"),
                "asset_id": asset_id,
            }
    return None


def _guard_generation(node_key: str, args: dict[str, Any]) -> dict[str, Any] | None:
    global _LAST_GENERATION_CALLED_DISTRIBUTION
    _LAST_GENERATION_CALLED_DISTRIBUTION = False
    nodes = all_nodes()
    node = nodes.get(node_key) or {}
    if node.get("distribution"):
        return {"status": "error", "error": "not_a_generation_node"}
    if is_blocked("media") and node.get("domain") in {"audio", "image", "video"}:
        return {"status": "error", "error": "kill_switch_active"}
    # Explicit refusal: generation must never call distribution
    if args.get("_call_distribution"):
        _LAST_GENERATION_CALLED_DISTRIBUTION = True
        return {"status": "error", "error": "generation_cannot_call_distribution"}
    denied = _require_consent(args, list(node.get("consent_purposes") or []))
    if denied:
        emit_scout_event("policy", {"node": node_key, "decision": "deny", "reason": denied.get("error")})
        return denied
    if node.get("consent_gated"):
        route_check = reject_if_incompatible(domain=str(node.get("domain")), purposes=list(node.get("consent_purposes") or []))
        if not route_check.get("ok"):
            return {"status": "error", "error": route_check.get("reason"), **route_check}
    return None


def _draft_envelope(node_key: str, text: str, args: dict[str, Any], *, audience: str = "public") -> dict[str, Any]:
    include_private = bool(args.get("include_private_approved")) and audience != "public"
    facts = {"summary": args.get("facts") or "Owner-stated fixture facts."}
    prefs = {"tone": "warm_professional"}
    style = {"persona_version": persona_version(), "voice": "ilaud"}
    private = {"note": "excluded_from_public"} if audience == "public" else {"note": args.get("private_note") or ""}
    body = {
        "status": "ok",
        "capability": node_key,
        "draft": text,
        "persona_version": persona_version(),
        "labels": _labels(
            stated_facts=facts,
            private_correspondence=private if include_private else {},
            inferred_preferences=prefs,
            generated_style=style,
            include_private_in_public=include_private,
        ),
        "distribution_invoked": False,
        "source": _SOURCE,
        "at": _iso_now(),
    }
    emit_scout_event("generation", {"node": node_key, "content_hash": hashlib.sha256(text.encode()).hexdigest()})
    return body


def persona_chat_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("persona_chat", args)
    if denied:
        return json.dumps(denied)
    prompt = str(args.get("prompt") or args.get("message") or "hello")
    text = f"[ilaud@0.1.0] {prompt}"
    return json.dumps(_draft_envelope("persona_chat", text, args, audience=str(args.get("audience") or "owner")))


def post_draft_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("post_draft", args)
    if denied:
        return json.dumps(denied)
    topic = str(args.get("topic") or "update")
    text = f"Public draft on {topic}. Disclosure: AI-assisted with owner approval required before publish."
    return json.dumps(_draft_envelope("post_draft", text, args, audience="public"))


def reply_draft_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("reply_draft", args)
    if denied:
        return json.dumps(denied)
    inbound = str(args.get("inbound_text") or "thanks")
    text = f"Draft reply: acknowledging '{inbound[:80]}'."
    return json.dumps(_draft_envelope("reply_draft", text, args, audience=str(args.get("audience") or "public")))


def email_draft_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("email_draft", args)
    if denied:
        return json.dumps(denied)
    subject = str(args.get("subject") or "Update")
    text = f"Subject: {subject}\n\nDraft email body in pinned iLaud style."
    return json.dumps(_draft_envelope("email_draft", text, args))


def content_repurpose_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("content_repurpose", args)
    if denied:
        return json.dumps(denied)
    source = str(args.get("source_text") or "source")
    text = f"Repurposed: {source[:120]}"
    return json.dumps(_draft_envelope("content_repurpose", text, args))


def digest_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("digest", args)
    if denied:
        return json.dumps(denied)
    text = "Weekly digest draft (fixture). Private correspondence excluded."
    return json.dumps(_draft_envelope("digest", text, args, audience="public"))


def decision_style_explain_handler(args: dict[str, Any], **_: Any) -> str:
    return json.dumps(
        {
            "status": "ok",
            "capability": "decision_style_explain",
            "explanation": "iLaud prefers short plain-English drafts with explicit disclosure.",
            "persona_version": persona_version(),
            "labels": _labels(stated_facts={"policy": "disclosure_required"}),
            "source": _SOURCE,
            "at": _iso_now(),
        }
    )


def fact_retrieve_handler(args: dict[str, Any], **_: Any) -> str:
    tenant = str(args.get("tenant_id") or "owner-laud")
    audience = str(args.get("audience") or "public")
    allow_rel = bool(args.get("allow_relationship"))
    # Adversarial: refuse private chat retrieve when not approved
    if args.get("request_private_chats") and not allow_rel:
        return json.dumps({"status": "error", "error": "private_chat_retrieve_denied"})
    hits = rag_search(
        query=str(args.get("query") or ""),
        tenant_id=tenant,
        audience=audience,
        allow_relationship=allow_rel,
    )
    return json.dumps(
        {
            "status": "ok",
            "capability": "fact_retrieve",
            "hits": hits,
            "labels": _labels(stated_facts={"hit_count": len(hits)}),
            "source": _SOURCE,
            "at": _iso_now(),
        }
    )


def speech_transcribe_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("speech_transcribe", args)
    if denied:
        return json.dumps(denied)
    audio_ref = str(args.get("audio_ref") or "fixture.wav")
    text = f"Transcript stub for {audio_ref}"
    return json.dumps(
        {
            "status": "ok",
            "capability": "speech_transcribe",
            "transcript": text,
            "media": _media_meta(domain="audio", text=text, consent_ids=[], prompt_template="asr_stub"),
            "source": _SOURCE,
            "at": _iso_now(),
        }
    )


def voice_note_draft_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("voice_note_draft", args)
    if denied:
        return json.dumps(denied)
    script = str(args.get("script") or "Hello from iLaud.")
    # Adversarial: refuse voice payment social engineering
    lowered = script.lower()
    if "payment" in lowered or "wire money" in lowered or "bank transfer" in lowered:
        return json.dumps({"status": "error", "error": "voice_payment_social_eng_denied"})
    out = _draft_envelope("voice_note_draft", script, args)
    out["media"] = _media_meta(
        domain="audio",
        text=script,
        consent_ids=[str(args.get("consent_id") or "")],
        prompt_template="voice_note_stub",
        fallback_text_only=True,
    )
    return json.dumps(out)


def voice_synthesise_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("voice_synthesise", args)
    if denied:
        # Deterministic fallback to text-only when consent/provider fails
        if denied.get("error") in {"consent_denied", "consent_incompatible_transfer"}:
            text = str(args.get("script") or "")
            return json.dumps(
                {
                    "status": "ok",
                    "capability": "voice_synthesise",
                    "fallback_text_only": True,
                    "draft": text,
                    "error_original": denied.get("error"),
                    "media": _media_meta(
                        domain="audio",
                        text=text,
                        consent_ids=[],
                        prompt_template="voice_synth_fallback",
                        fallback_text_only=True,
                    ),
                    "source": _SOURCE,
                    "at": _iso_now(),
                }
            )
        return json.dumps(denied)
    # Force stub path: never call real providers
    if args.get("force_provider_fail"):
        text = str(args.get("script") or "fallback")
        return json.dumps(
            {
                "status": "ok",
                "capability": "voice_synthesise",
                "fallback_text_only": True,
                "draft": text,
                "media": _media_meta(
                    domain="audio",
                    text=text,
                    consent_ids=[str(args.get("consent_id") or "")],
                    prompt_template="voice_synth_fallback",
                    fallback_text_only=True,
                ),
                "source": _SOURCE,
                "at": _iso_now(),
            }
        )
    script = str(args.get("script") or "Hello")
    out = _draft_envelope("voice_synthesise", script, args)
    out["media"] = _media_meta(
        domain="audio",
        text=script,
        consent_ids=[str(args.get("consent_id") or check_consent(str(args.get("asset_id") or ""), "generate").get("version") or "")],
        prompt_template="voice_synth_stub",
    )
    out["audio_uri"] = f"stub://voice/{hashlib.sha256(script.encode()).hexdigest()[:12]}"
    return json.dumps(out)


def image_brief_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("image_brief", args)
    if denied:
        return json.dumps(denied)
    brief = str(args.get("brief") or "portrait brief")
    return json.dumps(_draft_envelope("image_brief", brief, args))


def likeness_image_generate_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("likeness_image_generate", args)
    if denied:
        if denied.get("error") in {"consent_denied", "other_person_media_rejected", "consent_incompatible_transfer"}:
            if denied.get("error") == "other_person_media_rejected":
                return json.dumps(denied)
            text = str(args.get("prompt") or "likeness fallback")
            return json.dumps(
                {
                    "status": "ok",
                    "capability": "likeness_image_generate",
                    "fallback_text_only": True,
                    "draft": text,
                    "media": _media_meta(
                        domain="image",
                        text=text,
                        consent_ids=[],
                        prompt_template="likeness_fallback",
                        fallback_text_only=True,
                    ),
                    "source": _SOURCE,
                    "at": _iso_now(),
                }
            )
        return json.dumps(denied)
    if args.get("remove_watermark") or args.get("remove_disclosure"):
        return json.dumps({"status": "error", "error": "watermark_disclosure_removal_blocked"})
    prompt = str(args.get("prompt") or "owner likeness")
    out = _draft_envelope("likeness_image_generate", prompt, args)
    out["media"] = _media_meta(
        domain="image",
        text=prompt,
        consent_ids=[str(args.get("consent_id") or "")],
        prompt_template="likeness_stub",
    )
    out["image_uri"] = f"stub://image/{hashlib.sha256(prompt.encode()).hexdigest()[:12]}"
    return json.dumps(out)


def talking_head_script_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("talking_head_script", args)
    if denied:
        return json.dumps(denied)
    topic = str(args.get("topic") or "update")
    text = f"Talking-head script on {topic}. Include disclosure card."
    return json.dumps(_draft_envelope("talking_head_script", text, args))


def talking_head_generate_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("talking_head_generate", args)
    if denied:
        if denied.get("error") == "other_person_media_rejected":
            return json.dumps(denied)
        text = str(args.get("script") or "talking head fallback")
        return json.dumps(
            {
                "status": "ok",
                "capability": "talking_head_generate",
                "fallback_text_only": True,
                "draft": text,
                "media": _media_meta(
                    domain="video",
                    text=text,
                    consent_ids=[],
                    prompt_template="talking_head_fallback",
                    fallback_text_only=True,
                ),
                "source": _SOURCE,
                "at": _iso_now(),
            }
        )
    if args.get("remove_watermark") or args.get("remove_disclosure"):
        return json.dumps({"status": "error", "error": "watermark_disclosure_removal_blocked"})
    script = str(args.get("script") or "Hello viewers")
    out = _draft_envelope("talking_head_generate", script, args)
    out["media"] = _media_meta(
        domain="video",
        text=script,
        consent_ids=[str(args.get("consent_id") or "")],
        prompt_template="talking_head_stub",
    )
    out["video_uri"] = f"stub://video/{hashlib.sha256(script.encode()).hexdigest()[:12]}"
    return json.dumps(out)


def caption_and_package_handler(args: dict[str, Any], **_: Any) -> str:
    denied = _guard_generation("caption_and_package", args)
    if denied:
        return json.dumps(denied)
    captions = str(args.get("captions") or "Caption package stub")
    out = _draft_envelope("caption_and_package", captions, args)
    out["package"] = {"captions": captions, "disclosure": True, "watermark": True}
    return json.dumps(out)


def approval_submit_handler(args: dict[str, Any], **_: Any) -> str:
    content = str(args.get("content") or args.get("draft") or "")
    if not content:
        return json.dumps({"status": "error", "error": "content_required"})
    if args.get("bypass_approval"):
        return json.dumps({"status": "error", "error": "bypass_approval_denied"})
    row = submit_preview(
        content=content,
        channel=str(args.get("channel") or "web"),
        audience=str(args.get("audience") or "public"),
        persona_version=persona_version(),
        disclosure=bool(args.get("disclosure", True)),
        links=list(args.get("links") or []),
        private_reply=bool(args.get("private_reply")),
    )
    emit_scout_event("approval", {"approval_id": row["approval_id"], "content_hash": row["content_hash"]})
    return json.dumps({"status": "ok", "capability": "approval_submit", "approval": row, "source": _SOURCE, "at": _iso_now()})


def content_schedule_handler(args: dict[str, Any], **_: Any) -> str:
    if is_blocked("publish"):
        return json.dumps({"status": "error", "error": "kill_switch_active"})
    approval_id = str(args.get("approval_id") or "")
    if not approval_id:
        return json.dumps({"status": "error", "error": "approval_required"})
    return json.dumps(
        {
            "status": "ok",
            "capability": "content_schedule",
            "approval_id": approval_id,
            "schedule_at": args.get("schedule_at") or _iso_now(),
            "idempotency_key": args.get("idempotency_key") or f"sched_{uuid.uuid4().hex[:8]}",
            "source": _SOURCE,
            "at": _iso_now(),
        }
    )


def channel_publish_handler(args: dict[str, Any], **_: Any) -> str:
    result = outbox_publish(
        approval_id=str(args.get("approval_id") or ""),
        idempotency_key=str(args.get("idempotency_key") or f"pub_{uuid.uuid4().hex[:8]}"),
        channel=str(args.get("channel") or "web"),
        tenant_id=str(args.get("tenant_id") or "owner-laud"),
        actor_id=str(args.get("actor_id") or "owner"),
        shadow=bool(args.get("shadow")),
    )
    if not result.get("ok"):
        return json.dumps({"status": "error", **result})
    return json.dumps({"status": "ok", "capability": "channel_publish", **result, "source": _SOURCE, "at": _iso_now()})


def private_reply_send_handler(args: dict[str, Any], **_: Any) -> str:
    # Always high-risk / owner-reviewed; draft-only unless policy allows
    policy_allows = bool(args.get("policy_allows_send"))
    if not policy_allows:
        return json.dumps(
            {
                "status": "ok",
                "capability": "private_reply_send",
                "draft_only": True,
                "sent": False,
                "owner_reviewed_required": True,
                "risk": "high-risk",
                "source": _SOURCE,
                "at": _iso_now(),
            }
        )
    if not args.get("owner_reviewed"):
        return json.dumps({"status": "error", "error": "private_reply_requires_owner_review"})
    result = outbox_publish(
        approval_id=str(args.get("approval_id") or ""),
        idempotency_key=str(args.get("idempotency_key") or f"pr_{uuid.uuid4().hex[:8]}"),
        channel=str(args.get("channel") or "private"),
        tenant_id=str(args.get("tenant_id") or "owner-laud"),
        actor_id=str(args.get("actor_id") or "owner"),
        shadow=False,
    )
    if not result.get("ok"):
        return json.dumps({"status": "error", **result})
    return json.dumps(
        {
            "status": "ok",
            "capability": "private_reply_send",
            "draft_only": False,
            "sent": True,
            "owner_reviewed": True,
            **result,
            "source": _SOURCE,
            "at": _iso_now(),
        }
    )


def assert_no_forbidden_nodes() -> None:
    keys = set(all_nodes())
    forbidden = {
        "face-swap",
        "voice-clone-anyone",
        "upload-arbitrary-person",
        "remove-watermark",
        "credential-read",
        "unrestricted-publish",
    }
    overlap = keys & forbidden
    if overlap:
        raise RuntimeError(f"forbidden nodes present: {overlap}")
    # Generation keys must not include distribution
    for key in distribution_node_keys():
        if not all_nodes()[key].get("distribution"):
            raise RuntimeError(f"distribution flag missing: {key}")


# Touch unused imports for asset identity checks in likeness path
def _identity_asset_check(args: dict[str, Any]) -> dict[str, Any] | None:
    asset_id = str(args.get("asset_id") or "")
    if not asset_id:
        return None
    asset = get_asset(asset_id)
    if asset and asset.get("subject_id") != owner_subject_id():
        return {"status": "error", "error": "other_person_media_rejected"}
    return None
