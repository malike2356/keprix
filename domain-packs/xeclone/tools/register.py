"""Register Xeclone tools on the pack registry."""

from __future__ import annotations

from tools import handlers
from tools.registry import registry

_MAP = {
    "persona_chat": handlers.persona_chat_handler,
    "post_draft": handlers.post_draft_handler,
    "reply_draft": handlers.reply_draft_handler,
    "email_draft": handlers.email_draft_handler,
    "content_repurpose": handlers.content_repurpose_handler,
    "digest": handlers.digest_handler,
    "decision_style_explain": handlers.decision_style_explain_handler,
    "fact_retrieve": handlers.fact_retrieve_handler,
    "speech_transcribe": handlers.speech_transcribe_handler,
    "voice_note_draft": handlers.voice_note_draft_handler,
    "voice_synthesise": handlers.voice_synthesise_handler,
    "image_brief": handlers.image_brief_handler,
    "likeness_image_generate": handlers.likeness_image_generate_handler,
    "talking_head_script": handlers.talking_head_script_handler,
    "talking_head_generate": handlers.talking_head_generate_handler,
    "caption_and_package": handlers.caption_and_package_handler,
    "approval_submit": handlers.approval_submit_handler,
    "content_schedule": handlers.content_schedule_handler,
    "channel_publish": handlers.channel_publish_handler,
    "private_reply_send": handlers.private_reply_send_handler,
}

for name, handler in _MAP.items():
    registry.register(name, handler)

handlers.assert_no_forbidden_nodes()
