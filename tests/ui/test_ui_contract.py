"""UI contract and design system consistency tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits
from keprix.ui_contract import build_ui_contract
from keprix.ui_contract.actions import ACTIONS
from keprix.ui_contract.approvals import APPROVAL_CARD_FIELDS
from keprix.ui_contract.navigation import NAV_GROUP_LABELS, NAV_GROUPS_ORDER, navigation_for_role
from keprix.ui_contract.statuses import STATUS_VOCABULARY

ROOT = Path(__file__).resolve().parents[2]
TOKEN_DIR = ROOT / "ui" / "design-system" / "tokens"


@pytest.fixture
def ui_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()
    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_status_tokens_match_design_system_json():
    status_json = json.loads((TOKEN_DIR / "status.json").read_text(encoding="utf-8"))
    assert set(status_json.keys()) == set(STATUS_VOCABULARY.keys())
    for key, entry in status_json.items():
        assert STATUS_VOCABULARY[key]["label"] == entry["label"]


def test_navigation_groups_are_stable():
    admin_nav = navigation_for_role("admin")
    viewer_nav = navigation_for_role("viewer")
    admin_group_ids = {group["id"] for group in admin_nav["groups"]}
    viewer_group_ids = {group["id"] for group in viewer_nav["groups"]}
    assert "admin" in admin_group_ids
    assert "admin" not in viewer_group_ids
    assert set(NAV_GROUPS_ORDER) == set(NAV_GROUP_LABELS.keys())


def test_approval_card_fields_are_complete():
    contract = build_ui_contract({"role": "admin", "username": "admin"})
    assert set(APPROVAL_CARD_FIELDS).issubset(set(contract["approvals"]["fields"]))


def test_web_and_mobile_share_action_names():
    web_ids = {action["id"] for action in ACTIONS if "web" in action["surface"]}
    mobile_ids = {action["id"] for action in ACTIONS if "mobile" in action["surface"]}
    assert "nav.chat" in web_ids & mobile_ids
    assert "approval.approve" in web_ids & mobile_ids


def test_ui_contract_route_returns_payload(ui_client):
    response = ui_client.get("/api/ui/contract")
    assert response.status_code == 200
    payload = response.json()
    assert payload["product"] == "Keprix"
    assert "navigation" in payload
    assert "statuses" in payload
    assert payload["workspace"]["role"] == "admin"


def test_ui_copy_has_no_forbidden_characters():
    contract = build_ui_contract({"role": "user", "username": "user"})
    blob = json.dumps(contract)
    assert "\u2014" not in blob
    assert "\u2013" not in blob


def test_all_token_files_are_valid_json():
    for path in TOKEN_DIR.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))


def test_frontend_navigation_fallback_matches_backend_items():
    backend_ids = {item["id"] for item in navigation_for_role("admin")["items"]}
    nav_ts = (ROOT / "frontend" / "src" / "lib" / "navigation.ts").read_text(encoding="utf-8")
    for item_id in backend_ids:
        assert f'"{item_id}"' in nav_ts
