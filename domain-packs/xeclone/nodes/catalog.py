"""Xeclone/iLaud capability node catalog for the product sidecar."""

from __future__ import annotations

from typing import Any

TEXT_NODES: list[dict[str, Any]] = [
    {
        "key": "persona_chat",
        "title": "Persona chat",
        "domain": "text",
        "risk": "propose",
        "status": "live",
        "sync": True,
        "consent_purposes": ["generate"],
        "requires_approval": False,
        "distribution": False,
    },
    {
        "key": "post_draft",
        "title": "Post draft",
        "domain": "text",
        "risk": "propose",
        "status": "live",
        "sync": True,
        "consent_purposes": ["generate"],
        "requires_approval": False,
        "distribution": False,
    },
    {
        "key": "reply_draft",
        "title": "Reply draft",
        "domain": "text",
        "risk": "propose",
        "status": "live",
        "sync": True,
        "consent_purposes": ["generate"],
        "requires_approval": False,
        "distribution": False,
    },
    {
        "key": "email_draft",
        "title": "Email draft",
        "domain": "text",
        "risk": "propose",
        "status": "live",
        "sync": True,
        "consent_purposes": ["generate"],
        "requires_approval": False,
        "distribution": False,
    },
    {
        "key": "content_repurpose",
        "title": "Content repurpose",
        "domain": "text",
        "risk": "propose",
        "status": "live",
        "sync": True,
        "consent_purposes": ["generate", "transform"],
        "requires_approval": False,
        "distribution": False,
    },
    {
        "key": "digest",
        "title": "Digest",
        "domain": "text",
        "risk": "propose",
        "status": "live",
        "sync": True,
        "consent_purposes": ["generate"],
        "requires_approval": False,
        "distribution": False,
    },
    {
        "key": "decision_style_explain",
        "title": "Decision style explain",
        "domain": "text",
        "risk": "read",
        "status": "live",
        "sync": True,
        "consent_purposes": [],
        "requires_approval": False,
        "distribution": False,
    },
    {
        "key": "fact_retrieve",
        "title": "Fact retrieve",
        "domain": "text",
        "risk": "read",
        "status": "live",
        "sync": True,
        "consent_purposes": ["index"],
        "requires_approval": False,
        "distribution": False,
    },
]

AUDIO_NODES: list[dict[str, Any]] = [
    {
        "key": "speech_transcribe",
        "title": "Speech transcribe",
        "domain": "audio",
        "risk": "read",
        "status": "live",
        "sync": True,
        "consent_purposes": ["transform"],
        "provider": "stub-asr",
        "requires_approval": False,
        "distribution": False,
    },
    {
        "key": "voice_note_draft",
        "title": "Voice note draft",
        "domain": "audio",
        "risk": "propose",
        "status": "live",
        "sync": True,
        "consent_purposes": ["generate"],
        "provider": "stub-tts",
        "requires_approval": False,
        "distribution": False,
    },
    {
        "key": "voice_synthesise",
        "title": "Voice synthesise",
        "domain": "audio",
        "risk": "propose",
        "status": "live",
        "sync": True,
        "consent_purposes": ["generate", "upload_to_provider"],
        "provider": "stub-tts",
        "requires_approval": False,
        "distribution": False,
        "consent_gated": True,
    },
]

IMAGE_NODES: list[dict[str, Any]] = [
    {
        "key": "image_brief",
        "title": "Image brief",
        "domain": "image",
        "risk": "propose",
        "status": "live",
        "sync": True,
        "consent_purposes": ["generate"],
        "requires_approval": False,
        "distribution": False,
    },
    {
        "key": "likeness_image_generate",
        "title": "Likeness image generate",
        "domain": "image",
        "risk": "propose",
        "status": "live",
        "sync": True,
        "consent_purposes": ["generate", "upload_to_provider"],
        "provider": "stub-image",
        "requires_approval": False,
        "distribution": False,
        "consent_gated": True,
    },
]

VIDEO_NODES: list[dict[str, Any]] = [
    {
        "key": "talking_head_script",
        "title": "Talking head script",
        "domain": "video",
        "risk": "propose",
        "status": "live",
        "sync": True,
        "consent_purposes": ["generate"],
        "requires_approval": False,
        "distribution": False,
    },
    {
        "key": "talking_head_generate",
        "title": "Talking head generate",
        "domain": "video",
        "risk": "propose",
        "status": "live",
        "sync": True,
        "consent_purposes": ["generate", "upload_to_provider"],
        "provider": "stub-video",
        "requires_approval": False,
        "distribution": False,
        "consent_gated": True,
    },
    {
        "key": "caption_and_package",
        "title": "Caption and package",
        "domain": "video",
        "risk": "propose",
        "status": "live",
        "sync": True,
        "consent_purposes": ["transform"],
        "requires_approval": False,
        "distribution": False,
    },
]

DISTRIBUTION_NODES: list[dict[str, Any]] = [
    {
        "key": "approval_submit",
        "title": "Approval submit",
        "domain": "distribution",
        "risk": "mutate",
        "status": "live",
        "sync": True,
        "consent_purposes": [],
        "requires_approval": False,
        "distribution": True,
    },
    {
        "key": "content_schedule",
        "title": "Content schedule",
        "domain": "distribution",
        "risk": "outbound",
        "status": "live",
        "sync": True,
        "consent_purposes": ["publish"],
        "requires_approval": True,
        "distribution": True,
    },
    {
        "key": "channel_publish",
        "title": "Channel publish",
        "domain": "distribution",
        "risk": "outbound",
        "status": "live",
        "sync": True,
        "consent_purposes": ["publish"],
        "requires_approval": True,
        "distribution": True,
    },
    {
        "key": "private_reply_send",
        "title": "Private reply send",
        "domain": "distribution",
        "risk": "high-risk",
        "status": "live",
        "sync": True,
        "consent_purposes": ["private_message"],
        "requires_approval": True,
        "distribution": True,
        "draft_only_default": True,
        "owner_reviewed": True,
    },
]

FORBIDDEN_KEYS = frozenset(
    {
        "face-swap",
        "voice-clone-anyone",
        "upload-arbitrary-person",
        "remove-watermark",
        "credential-read",
        "unrestricted-publish",
        "unrestricted publish",
    }
)


def all_nodes() -> dict[str, dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    for group in (TEXT_NODES, AUDIO_NODES, IMAGE_NODES, VIDEO_NODES, DISTRIBUTION_NODES):
        for node in group:
            if node["key"] in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden node key: {node['key']}")
            entry = dict(node)
            entry.setdefault("version", "1.0.0")
            entry.setdefault("product", "xeclone")
            entry.setdefault("sync", True)
            entry.setdefault("consent_purposes", [])
            entry.setdefault("provider", None)
            entry.setdefault("requires_approval", False)
            entry.setdefault("distribution", False)
            entry.setdefault("consent_gated", False)
            entry["required_grants"] = (f"node:{entry['key']}",)
            nodes[entry["key"]] = entry
    return nodes


def generation_node_keys() -> frozenset[str]:
    return frozenset(k for k, n in all_nodes().items() if not n.get("distribution"))


def distribution_node_keys() -> frozenset[str]:
    return frozenset(k for k, n in all_nodes().items() if n.get("distribution"))
