"""CRM Connections: workspace credentials + flags for Nice adapters."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "0")
    monkeypatch.setenv("ENCRYPTION_KEY", "test-crm-connections-key")
    from keprix.crm import store as store_mod
    from keprix.crm.store import CrmStore

    crm = CrmStore(tmp_path / "connections.sqlite")
    monkeypatch.setattr(store_mod, "get_crm_store", lambda path=None: crm)
    return crm


def test_put_credential_masks_and_configures_hubspot(store, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KEPRIX_HUBSPOT_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("HUBSPOT_ACCESS_TOKEN", raising=False)
    from keprix.crm.connections import connections_status, get_slot_value, put_credential
    from keprix.crm.integrations import get_adapter

    ws = "ws-conn"
    assert get_adapter("hubspot").configured(ws) is False

    status = put_credential(store, ws, "hubspot_access_token", "hs-secret-token-9876", actor_id="op1")
    assert status["configured"] is True
    assert status["source"] == "workspace"
    assert status["masked"] == "****9876"
    assert "hs-secret" not in str(status)

    listed = connections_status(store, ws)
    hub = next(s for s in listed["groups"]["crm_integrations"] if s["slot_id"] == "hubspot_access_token")
    assert hub["masked"] == "****9876"
    assert "hs-secret-token-9876" not in str(listed)

    assert get_slot_value(store, ws, "hubspot_access_token") == "hs-secret-token-9876"
    assert get_adapter("hubspot").configured(ws) is True
    assert get_adapter("hubspot").status(ws)["status"] != "not_configured"


def test_flag_enables_whatsapp_channel(store) -> None:
    from keprix.crm.connections import put_credential, set_flag, workspace_flag_enabled
    from keprix.crm.messaging_channels import channel_flag_enabled, provider_status

    ws = "ws-wa"
    assert channel_flag_enabled(ws) is False
    set_flag(store, ws, "whatsapp_sms_enabled", True, actor_id="op1")
    assert workspace_flag_enabled(store, ws, "whatsapp_sms_enabled") is True
    assert channel_flag_enabled(ws) is True

    put_credential(store, ws, "whatsapp_token", "wa-token-abcd", actor_id="op1")
    put_credential(store, ws, "twilio_auth_token", "twilio-auth-zzzz", actor_id="op1")
    put_credential(store, ws, "twilio_account_sid", "ACxxxxxxxx", actor_id="op1")
    st = provider_status(ws)
    assert st["flag_enabled"] is True
    assert st["whatsapp"]["status"] == "ready"
    assert st["sms"]["status"] == "ready"


def test_clearbit_and_social_flags(store, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KEPRIX_CLEARBIT_API_KEY", raising=False)
    monkeypatch.delenv("CLEARBIT_API_KEY", raising=False)
    monkeypatch.delenv("LINKEDIN_CLIENT_ID", raising=False)
    monkeypatch.delenv("LINKEDIN_CLIENT_SECRET", raising=False)
    from keprix.crm.connections import put_credential, set_flag
    from keprix.crm.licensed_enrich import list_providers
    from keprix.discovery.adapters.social import LinkedInApiAdapter

    ws = "ws-enr"
    providers = {p["name"]: p for p in list_providers(ws)}
    assert providers["clearbit_slot"]["status"] == "not_configured"

    put_credential(store, ws, "clearbit_api_key", "cb-key-1111", actor_id="op1")
    providers = {p["name"]: p for p in list_providers(ws)}
    assert providers["clearbit_slot"]["configured"] is True
    assert providers["clearbit_slot"]["configure_path"] == "/crm/settings#connections"

    li = LinkedInApiAdapter()
    assert li.health(ws).configured is False
    put_credential(store, ws, "linkedin_client_id", "li-id", actor_id="op1")
    put_credential(store, ws, "linkedin_client_secret", "li-secret", actor_id="op1")
    set_flag(store, ws, "linkedin_api_enabled", True, actor_id="op1")
    health = li.health(ws)
    assert health.configured is True


def test_property_portal_flag(store) -> None:
    from keprix.crm.connections import set_flag, workspace_flag_enabled
    from keprix.discovery.adapters.property_portals import property_portals_enabled

    ws = "ws-pp"
    assert property_portals_enabled(ws) is False
    set_flag(store, ws, "property_portal_adapters_enabled", True, actor_id="op1")
    assert workspace_flag_enabled(store, ws, "property_portal_adapters_enabled") is True
    assert property_portals_enabled(ws) is True
