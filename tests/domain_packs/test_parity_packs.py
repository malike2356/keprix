"""Filesystem domain packs + lead tools."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.backend.domain_packs.filesystem import list_filesystem_packs
from keprix.product_leads.store import LeadStore
from keprix.tools.product_lead_tools import _handle_create, _handle_list


def test_filesystem_packs_present() -> None:
    names = {p.get("domain_name") for p in list_filesystem_packs()}
    assert "research-intel" in names
    assert "scheduling-ops" in names


def test_create_lead_tool(tmp_path: Path, monkeypatch) -> None:
    store = LeadStore(path=tmp_path / "leads.json")
    monkeypatch.setattr("keprix.product_leads.store.get_lead_store", lambda: store)
    raw = _handle_create({"name": "Ada Lovelace", "email": "ada@example.com"})
    payload = json.loads(raw)
    assert payload["name"] == "Ada Lovelace"
    listed = json.loads(_handle_list({"limit": 5}))
    assert listed["items"]
