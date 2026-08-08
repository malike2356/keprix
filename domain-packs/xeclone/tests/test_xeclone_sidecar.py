"""HTTP contract tests for the Xeclone Keprix sidecar."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

PACK_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_NODES = {
    "persona_chat",
    "post_draft",
    "reply_draft",
    "email_draft",
    "content_repurpose",
    "digest",
    "decision_style_explain",
    "fact_retrieve",
    "speech_transcribe",
    "voice_note_draft",
    "voice_synthesise",
    "image_brief",
    "likeness_image_generate",
    "talking_head_script",
    "talking_head_generate",
    "caption_and_package",
    "approval_submit",
    "content_schedule",
    "channel_publish",
    "private_reply_send",
}


def _load_app():
    if str(PACK_ROOT) not in sys.path:
        sys.path.insert(0, str(PACK_ROOT))
    for name in list(sys.modules):
        if name == "http_app" or name.startswith(("consent", "tools", "nodes", "bridge", "approvals")):
            # allow fresh imports when needed; keep simple for TestClient
            pass
    import http_app

    return http_app.app


def test_health_and_capabilities() -> None:
    client = TestClient(_load_app())
    health = client.get("/v1/products/xeclone/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ok"
    assert body["sidecar"] == "keprix-xeclone"
    assert body["persona_version"] == "ilaud@0.1.0"
    assert body["autonomous_mode"] is False

    caps = client.get("/v1/products/xeclone/capabilities")
    assert caps.status_code == 200
    keys = {n["key"] for n in caps.json()["nodes"]}
    assert REQUIRED_NODES.issubset(keys)
    for forbidden in ("face-swap", "voice-clone-anyone", "remove-watermark", "credential-read"):
        assert forbidden not in keys


def test_invoke_persona_chat() -> None:
    client = TestClient(_load_app())
    response = client.post(
        "/v1/products/xeclone/invoke",
        json={"capability": "persona_chat", "input": {"prompt": "hello world"}},
    )
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["status"] == "ok"
    assert "hello world" in result["draft"]
    assert "stated_facts" in result["labels"]
    assert result["distribution_invoked"] is False


def test_event_dedupe_and_job_cancel() -> None:
    client = TestClient(_load_app())
    evt = {"id": "e1", "type": "draft.created", "source": "xeclone", "tenant": "owner-laud"}
    assert client.post("/v1/products/xeclone/events", json=evt).json()["deduped"] is False
    assert client.post("/v1/products/xeclone/events", json=evt).json()["deduped"] is True

    job = client.post(
        "/v1/products/xeclone/jobs",
        json={
            "capability": "persona_chat",
            "input": {"prompt": "queued"},
            "tenant_id": "owner-laud",
        },
    ).json()
    cancelled = client.post(f"/v1/products/xeclone/jobs/{job['job_id']}/cancel").json()
    assert cancelled["status"] in {"completed", "cancelled"}


def test_fixture_product_health() -> None:
    client = TestClient(_load_app())
    response = client.get("/fixture-product/api/keprix/v1/health")
    assert response.status_code == 200
    assert response.json()["product"] == "xeclone"
    assert response.json()["tenant"] == "owner-laud"
