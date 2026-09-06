from __future__ import annotations

from pathlib import Path

from keprix.crm.store import reset_crm_store_for_tests
from keprix.integrations.google_workspace import vault_export
from keprix.integrations.google_workspace.tools_contacts import gws_contacts_enrich


class FakeContacts:
    def contacts_list(self, query: str, max_results: int) -> dict:
        assert query == "Ada Lovelace"
        assert max_results == 20
        return {
            "contacts": [
                {
                    "names": [{"givenName": "Ada", "familyName": "Lovelace"}],
                    "emailAddresses": [{"value": "ada@example.test"}],
                }
            ]
        }


def test_contacts_enrich_fills_empty_fields_without_overwriting(tmp_path: Path):
    store = reset_crm_store_for_tests(tmp_path / "crm.sqlite")
    lead = store.create_lead("ws1", name="Existing Name", source="test")
    result = gws_contacts_enrich(
        "ws1", lead["id"], "Ada Lovelace", bridge=FakeContacts(), store=store
    )
    assert result["status"] == "enriched"
    updated = store.get_lead("ws1", lead["id"])
    assert updated["name"] == "Existing Name"
    assert updated["emails"] == ["ada@example.test"]
    assert updated["custom_fields"]["google_contact"]["names"][0]["givenName"] == "Ada"


def test_contacts_enrich_reports_no_match(tmp_path: Path):
    store = reset_crm_store_for_tests(tmp_path / "crm.sqlite")
    lead = store.create_lead("ws1", name="Missing", source="test")
    result = gws_contacts_enrich(
        "ws1",
        lead["id"],
        "Missing",
        bridge=type("B", (), {"contacts_list": lambda *_: {"contacts": []}})(),
        store=store,
    )
    assert result["status"] == "no_match"


def test_vault_exports_store_google_reference(tmp_path: Path):
    class ItemStore:
        def __init__(self):
            self.item = {"id": "item1", "name": "Brief", "metadata": {}}

        def get_item(self, workspace_id, item_id, include_trashed=False):
            return self.item if item_id == "item1" else None

        def update_item(self, workspace_id, item_id, **kwargs):
            self.item["metadata"] = kwargs["metadata"]

    class Vault:
        def __init__(self):
            self.store = ItemStore()

        def read_text(self, workspace_id, item_id):
            return "Heading\n\nDetails"

    class Bridge:
        def docs_create(self, title, text, confirm):
            assert (title, text, confirm) == ("Brief", "Heading\n\nDetails", True)
            return {"document_id": "doc1", "url": "https://docs.google.test/doc1"}

        def slides_create(self, title, slides, confirm):
            assert slides == ["Heading", "Details"]
            return {"presentation_id": "slide1"}

    vault = Vault()
    result = vault_export.create_doc_from_vault(
        "ws1", "item1", confirm=True, vault=vault, bridge=Bridge()
    )
    assert result["document_id"] == "doc1"
    assert vault.store.item["metadata"]["google_doc"]["id"] == "doc1"
    result = vault_export.create_slides_from_vault(
        "ws1", "item1", confirm=True, vault=vault, bridge=Bridge()
    )
    assert result["presentation_id"] == "slide1"
    assert vault.store.item["metadata"]["google_slides"]["id"] == "slide1"
