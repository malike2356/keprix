from pathlib import Path

import pytest

from keprix.crm.capture import (
    create_capture_link,
    list_capture_links,
    rotate_capture_link,
    set_capture_link_active,
    submit_capture,
    token_hash,
)
from keprix.crm.store import reset_crm_store_for_tests
from keprix.crm.capture_routes import _redirect_ok


@pytest.fixture()
def store(tmp_path: Path):
    return reset_crm_store_for_tests(tmp_path / "capture.sqlite")


def test_capture_creates_consent_lead_and_does_not_store_raw_token(store) -> None:
    link = create_capture_link(store, "ws_a", label="Landing page")

    result = submit_capture(
        store,
        link["token"],
        email="Prospect@example.com",
        fullname=" Prospect One ",
        consent=True,
        ip="198.51.100.10",
        company="Example Ltd",
        phone="+441234567890",
        campaign="spring",
    )

    assert result["status"] == "new"
    lead = store.get_lead("ws_a", result["lead_id"])
    assert lead["emails"][0]["address"] == "prospect@example.com"
    assert lead["consent_status"] == "consented"
    assert lead["company_name"] == "Example Ltd"
    assert store._conn.execute("SELECT COUNT(*) FROM crm_capture_links WHERE token_hash = ?", (link["token"],)).fetchone()[0] == 0
    assert store._conn.execute("SELECT token_hash FROM crm_capture_links").fetchone()[0] == token_hash(link["token"])


def test_capture_is_idempotent_for_same_workspace_and_email(store) -> None:
    link = create_capture_link(store, "ws_a")
    first = submit_capture(store, link["token"], email="same@example.com", fullname="Same", consent=True, ip="203.0.113.1")
    second = submit_capture(store, link["token"], email="SAME@example.com", fullname="Same", consent=True, ip="203.0.113.2")

    assert second["status"] == "duplicate"
    assert second["duplicate_of"] == first["lead_id"]
    assert len(store.list_leads("ws_a")) == 1
    assert len(store.list_leads("ws_b")) == 0


def test_capture_requires_consent_and_disabled_or_rotated_tokens_fail(store) -> None:
    link = create_capture_link(store, "ws_a")
    with pytest.raises(ValueError):
        submit_capture(store, link["token"], email="a@example.com", fullname="A", consent=False)

    assert set_capture_link_active(store, "ws_a", link["id"], False)
    with pytest.raises(LookupError):
        submit_capture(store, link["token"], email="a@example.com", fullname="A", consent=True)

    active = create_capture_link(store, "ws_a", label="old")
    rotated = rotate_capture_link(store, "ws_a", active["id"])
    assert rotated and rotated["token"] != active["token"]
    assert len([item for item in list_capture_links(store, "ws_a") if item["active"]]) == 1
    with pytest.raises(LookupError):
        submit_capture(store, active["token"], email="old@example.com", fullname="Old", consent=True)


def test_capture_redirect_requires_same_origin_or_explicit_allowlist(monkeypatch) -> None:
    assert _redirect_ok("/thanks")
    assert not _redirect_ok("https://example.com/thanks")
    monkeypatch.setenv("KEPRIX_CAPTURE_ALLOWED_REDIRECT_ORIGINS", "https://example.com")
    assert _redirect_ok("https://example.com/thanks")
