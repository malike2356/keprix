"""Tests for the Keprix Clinicom sidecar pack."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PACK_ROOT = Path(__file__).resolve().parents[1]


def _load_http_app():
    sys.path.insert(0, str(PACK_ROOT))
    try:
        spec = importlib.util.spec_from_file_location("clinicom_http_app", PACK_ROOT / "http_app.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.app
    finally:
        if str(PACK_ROOT) in sys.path:
            sys.path.remove(str(PACK_ROOT))


def test_health_endpoint() -> None:
    client = TestClient(_load_http_app())
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["sidecar"] == "keprix-clinicom"
    assert body["contract_version"] == "2.0"


def test_capabilities_endpoint() -> None:
    client = TestClient(_load_http_app())
    response = client.get("/clinicom/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["contract_version"] == "2.0"
    tool_names = {tool["name"] for tool in body["tools"]}
    assert "clinicom_session_digest" in tool_names
    assert "clinicom_confidence_explain" in tool_names
    assert body["profile"] == "keprix"
    assert body["nodes"]
    assert all("safety_class" in tool for tool in body["tools"])


def test_translate_same_language() -> None:
    client = TestClient(_load_http_app())
    response = client.post(
        "/clinicom/tools/translate",
        json={
            "text": "My chest hurts",
            "source_language": "en",
            "target_language": "en",
        },
    )
    assert response.status_code == 200
    assert response.json()["translated_text"] == "My chest hurts"


def test_simplify_returns_readability() -> None:
    client = TestClient(_load_http_app())
    response = client.post(
        "/clinicom/tools/simplify",
        json={
            "text": "Patient presents with hypertension and dyspnea.",
            "target_reading_level": 8,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "simplified_text" in body
    assert "readability_scores" in body


def test_deep_tool_route_dispatches() -> None:
    client = TestClient(_load_http_app())
    response = client.post(
        "/clinicom/tools/teachback_score",
        json={
            "patient_response": "I will take the tablets at night and come back if it gets worse.",
            "key_points": ["take the tablets", "come back if it gets worse"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "score" in body
    assert body["source"]


def test_registry_dispatch_json_strings() -> None:
    sys.path.insert(0, str(PACK_ROOT))
    try:
        import tools.register  # noqa: F401
        from tools.registry import registry

        raw = registry.dispatch(
            "clinicom_speak",
            {"text": "Hello", "language": "en"},
        )
        data = json.loads(raw)
        assert data["language"] == "en"
        assert data["audio_base64"]
        deep_raw = registry.dispatch(
            "clinicom_confidence_explain",
            {"score": 82, "provider_sources": {"translation": "keprix"}},
        )
        deep_data = json.loads(deep_raw)
        assert deep_data["score"] == 82
    finally:
        if str(PACK_ROOT) in sys.path:
            sys.path.remove(str(PACK_ROOT))
