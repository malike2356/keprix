from fastapi.testclient import TestClient

from keprix.api.auth import require_admin
from keprix.api.server import create_app
from keprix.voice.session import list_voice_sessions, reset_voice_sessions


def test_twilio_webhook_returns_twiml_media_stream() -> None:
    reset_voice_sessions()
    client = TestClient(create_app())

    response = client.post("/api/gateway/twilio/voice", data={"From": "+155501", "To": "+155502"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<Stream" in response.text
    assert "Aiva speaking" in response.text
    sessions = list_voice_sessions()
    assert sessions and sessions[0].caller == "+155501"


def test_voice_admin_routes_create_and_list_sessions() -> None:
    reset_voice_sessions()
    app = create_app()
    app.dependency_overrides[require_admin] = lambda: {"id": "admin", "role": "admin"}
    client = TestClient(app)

    created = client.post("/api/voice/phone/sessions", json={"caller": "+155501", "called": "+155502"})
    listed = client.get("/api/voice/phone/sessions")
    cost = client.get("/api/voice/phone/cost-estimate?seconds=300")

    assert created.status_code == 200
    assert listed.status_code == 200
    assert listed.json()["sessions"][0]["caller"] == "+155501"
    assert cost.json()["total_usd"] < 0.20
